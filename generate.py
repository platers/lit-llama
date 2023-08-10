from jsonargparse import CLI
import sys
import time
import warnings
from pathlib import Path
from typing import Optional
import itertools

import lightning as L
import torch

import torch._dynamo.config
# torch._dynamo.config.automatic_dynamic_shapes = True
import torch._inductor.config
# torch._inductor.config.triton.unique_kernel_names = True

# Enable this to bring perf from 93 tok/s => 103 tok/s
# increases compile time due to coord descent autotuning + compiling both prefill and decode steps

# support running without installing as a package
wd = Path(__file__).parent.parent.resolve()
sys.path.append(str(wd))

from model import LLaMA
from tokenizer import Tokenizer
from utils import lazy_load, llama_model_lookup

def fast_multinomial_sample_one(probs_sort):
    q = torch.empty_like(probs_sort).exponential_(1)
    return torch.argmax(probs_sort / q, dim=-1, keepdim=True)

def sample(logits, temperature: float = 1.0, top_k: Optional[int] = None):
    logits =  logits[0, -1] / temperature

    # optionally crop the logits to only the top k options
    if top_k is not None:
        v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
        logits = torch.where(logits < v[-1], -float("Inf"), logits)


    probs = torch.nn.functional.softmax(logits, dim=-1)
    # print()
    idx_next = fast_multinomial_sample_one(probs).to(dtype=torch.int)
    # idx_next = torch.multinomial(probs, num_samples=1).to(dtype=torch.int)
    return idx_next

def prefill(
    model: LLaMA,
    input_pos: torch.Tensor,
    x: torch.Tensor,
    **kwargs
):
    # input_pos: [B, S]
    logits = model(x, input_pos)
    return sample(logits, **kwargs)

def decode_one_token(
    model: LLaMA,
    input_pos: torch.Tensor,
    x: torch.Tensor,
    **kwargs
) -> torch.Tensor:
    # input_pos: [B, 1]
    assert input_pos.shape[-1] == 1
    logits = model(x, input_pos)
    return sample(logits, **kwargs)

@torch.no_grad()
def generate(
    model: LLaMA,
    prompt: torch.Tensor,
    max_new_tokens: int,
    *,
    max_seq_length: Optional[int] = None,
    temperature: float = 1.0,
    top_k: Optional[int] = None,
    eos_id: Optional[int] = None,
) -> torch.Tensor:
    """Takes a conditioning sequence (prompt) as input and continues to generate as many tokens as requested.

    The implementation of this function is modified from A. Karpathy's nanoGPT.

    Args:
        model: The model to use.
        prompt: Tensor of shape (T) with indices of the prompt sequence.
        max_new_tokens: The number of new tokens to generate.
        max_seq_length: The maximum sequence length allowed.
        temperature: Scales the predicted logits by 1 / temperature
        top_k: If specified, only sample among the tokens with the k highest probabilities
        eos_id: If specified, stop generating any more token once the <eos> token is triggered
    """
    # create an empty tensor of the expected final shape and fill in the current tokens
    T = prompt.size(0)
    T_new = T + max_new_tokens
    if max_seq_length is None:
        max_seq_length = min(T_new, model.config.block_size)
    model.setup_caches(max_batch_size=1, max_seq_length=max_seq_length)

    device, dtype = prompt.device, prompt.dtype
    # create an empty tensor of the expected final shape and fill in the current tokens
    empty = torch.empty(T_new, dtype=dtype, device=device)
    empty[:T] = prompt
    seq = empty
    input_pos = torch.arange(0, T, device=device)

    next_token = prefill(model, input_pos, prompt.view(1, -1), temperature=temperature, top_k=top_k)
    seq[T] = next_token

    input_pos = torch.tensor([T], device=device, dtype=input_pos.dtype)

    # generate max_new_tokens tokens
    for _ in range(max_new_tokens - 1):
        cur_token = next_token.view(1, -1)

        # forward
        next_token = decode_one_token(model, input_pos, cur_token, temperature=temperature, top_k=top_k)

        # advance
        input_pos = input_pos + 1

        # concatenate the new generation
        seq[input_pos] = next_token

        # if <eos> token is triggered, return the output (stop generation)
        if next_token == eos_id:
            return seq[:input_pos]  # include the EOS token

    return seq


def main(
    prompt: str = "Hello, my name is",
    prompt_synthetic: Optional[int] = None,
    num_samples: int = 3,
    max_new_tokens: int = 50,
    top_k: int = 200,
    temperature: float = 0.8,
    checkpoint_path: Path = Path("checkpoints/lit-llama/7B/lit-llama.pth"),
    tokenizer_path: Path = Path("tokenizer.model"),
    fake: Optional[str] = None,
    compile: bool = True,
    profile: Optional[Path] = None,
    max_optimize: bool = True,
) -> None:
    """Generates text samples based on a pre-trained LLaMA model and tokenizer.

    Args:
        prompt: The prompt string to use for generating the samples.
        num_samples: The number of text samples to generate.
        max_new_tokens: The number of generation steps to take.
        top_k: The number of top most probable tokens to consider in the sampling process.
        temperature: A value controlling the randomness of the sampling process. Higher values result in more random
            samples.
        checkpoint_path: The checkpoint path to load.
        tokenizer_path: The tokenizer path to load.
        quantize: Whether to quantize the model and using which method:
            ``"llm.int8"``: LLM.int8() mode,
            ``"gptq.int4"``: GPTQ 4-bit mode.
    """
    assert tokenizer_path.is_file(), tokenizer_path

    precision = "bf16-true" if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else "32-true"
    fabric = L.Fabric(devices=1, precision=precision)

    print("Loading model ...", file=sys.stderr)
    t0 = time.time()
    if fake is not None:
        name = fake
        with fabric.init_module(empty_init=True):
            model = LLaMA.from_name(name)
    else:
        assert checkpoint_path.is_file(), checkpoint_path
        with lazy_load(checkpoint_path) as checkpoint:
            name = llama_model_lookup(checkpoint)

            with fabric.init_module(empty_init=True):
                model = LLaMA.from_name(name)
    print(f"Time to load model: {time.time() - t0:.02f} seconds.", file=sys.stderr)


    model.eval()

    tokenizer = Tokenizer(tokenizer_path)
    encoded = tokenizer.encode(prompt, bos=True, eos=False, device=fabric.device)
    if prompt_synthetic is not None:
        encoded = torch.randint(encoded.amax().item(), (prompt_synthetic,), dtype=encoded.dtype, device=encoded.device)
    prompt_length = encoded.size(0)

    L.seed_everything(1234)
    model_size = sum([p.numel() * p.data.element_size() for p in itertools.chain(model.parameters(), model.buffers())])
    if compile:
        global decode_one_token, prefill
        decode_one_token = torch.compile(decode_one_token, mode="reduce-overhead")

        if max_optimize:
            # This seems to have some errors sometimes
            # prefill = torch.compile(prefill, mode="reduce-overhead")
            torch._inductor.config.coordinate_descent_tuning = True


    for i in range(num_samples):
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        import contextlib
        prof = contextlib.nullcontext() if i != num_samples - 1 or not profile else torch.profiler.profile()
        with prof:
            y = generate(model, encoded, max_new_tokens, temperature=temperature, top_k=top_k)
        if hasattr(prof, "export_chrome_trace"):
            prof.export_chrome_trace(f"{profile}.json")
        torch.cuda.synchronize()
        t = time.perf_counter() - t0

        model.reset_cache()
        print(tokenizer.decode(y))
        tokens_generated = y.size(0) - prompt_length
        tokens_sec = tokens_generated / t
        print(f"Time for inference {i + 1}: {t:.02f} sec total, {tokens_generated / t:.02f} tokens/sec", file=sys.stderr)
        print(f"Bandwidth achieved: {model_size * tokens_sec / 1e9:.02f} GB/s")

    print(f"Memory used: {torch.cuda.max_memory_reserved() / 1e9:.02f} GB", file=sys.stderr)


if __name__ == "__main__":
    from jsonargparse import CLI

    torch.set_float32_matmul_precision("high")
    warnings.filterwarnings(
        # Triggered internally at ../aten/src/ATen/EmptyTensor.cpp:31
        "ignore",
        message="ComplexHalf support is experimental and many operators don't support it yet"
    )
    warnings.filterwarnings(
        # Triggered in bitsandbytes/autograd/_functions.py:298
        "ignore",
        message="MatMul8bitLt: inputs will be cast from torch.bfloat16 to float16 during quantization",
    )
    CLI(main)
