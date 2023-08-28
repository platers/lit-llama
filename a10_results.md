# Original model

## 7B

`python generate.py --prompt "Hello, my name is" --max_new_tokens 200 --num_samples 10 --fake 7B  --compile true`

Time for inference 10: 6.05 sec total, 33.08 tokens/sec
Bandwidth achieved: 445.82 GB/s
Memory used: 14.04 GB


`python generate.py --prompt "Hello, my name is" --max_new_tokens 200 --num_samples 10 --fake 7B  --compile false`

Time for inference 10: 6.59 sec total, 30.34 tokens/sec
Bandwidth achieved: 408.89 GB/s
Memory used: 13.63 GB

## 1B

`python generate.py --prompt "Hello, my name is" --max_new_tokens 200 --num_samples 10 --fake 1B  --compile true`

Time for inference 10: 1.91 sec total, 104.62 tokens/sec
Bandwidth achieved: 334.12 GB/s
Memory used: 3.89 GB

`python generate.py --prompt "Hello, my name is" --max_new_tokens 200 --num_samples 10 --fake 1B  --compile false`

Time for inference 10: 6.56 sec total, 30.51 tokens/sec
Bandwidth achieved: 97.42 GB/s
Memory used: 3.54 GB

# Remove RoPE

`python generate.py --prompt "Hello, my name is" --max_new_tokens 200 --num_samples 10 --fake 1B  --compile true`

Time for inference 10: 1.87 sec total, 106.86 tokens/sec
Bandwidth achieved: 341.26 GB/s
Memory used: 3.89 GB

`python generate.py --prompt "Hello, my name is" --max_new_tokens 200 --num_samples 10 --fake 1B  --compile false`

Time for inference 10: 3.84 sec total, 52.02 tokens/sec
Bandwidth achieved: 166.13 GB/s
Memory used: 3.54 GB

# Replace RMSNorm with LayerNorm

`python generate.py --prompt "Hello, my name is" --max_new_tokens 200 --num_samples 10 --fake 1B  --compile true`

Time for inference 10: 1.88 sec total, 106.66 tokens/sec
Bandwidth achieved: 340.62 GB/s
Memory used: 3.63 GB

`python generate.py --prompt "Hello, my name is" --max_new_tokens 200 --num_samples 10 --fake 1B  --compile false`

Time for inference 10: 3.23 sec total, 61.86 tokens/sec
Bandwidth achieved: 197.55 GB/s
Memory used: 3.54 GB

## Longer context

`python generate.py --prompt "Hello, my name is" --max_new_tokens 2000 --num_samples 10 --fake 1B  --compile true`

Time for inference 10: 40.49 sec total, 49.40 tokens/sec
Bandwidth achieved: 157.76 GB/s
Memory used: 5.36 GB

`python generate.py --prompt "Hello, my name is" --max_new_tokens 2000 --num_samples 10 --fake 1B  --compile false`

Time for inference 10: 31.52 sec total, 63.45 tokens/sec
Bandwidth achieved: 202.64 GB/s
Memory used: 4.14 GB