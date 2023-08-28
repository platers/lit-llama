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