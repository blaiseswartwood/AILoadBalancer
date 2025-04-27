# AILoadBalancer
Creating a load balancer specifically geared towards for LLM usage

Make a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\activate.ps1
```

```powershell
pip install huggingface_hub transformers torch
```

Generate a huggingface token and allow use of GPT2

```powershell
notepad $PROFILE
$env:HF_TOKEN = 'your_token_here'
```