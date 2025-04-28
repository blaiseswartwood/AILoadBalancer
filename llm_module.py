import os 
from huggingface_hub import login
from transformers import pipeline
import torch

MAX_RESPONSE = 50

print("Logging into HuggingFace Hub...")
#login(token='your_token') # Replace 'your_token' with your actual token
login(token=os.environ.get('HF_TOKEN'))

print("Loading LLM model...")
model_ID= 'gpt2'

generator = pipeline(
    'text-generation',
    model=model_ID,
    device=0,  # use GPU
    torch_dtype=torch.bfloat16
)

print("Model loaded successfully.")
print("Clients may now connect to the server.")

def get_llm_response(prompt: str) -> str:
    """Returns the response from the LLM model for the given prompt.

    Args:
        prompt (str): The input prompt for the LLM model.
    """
    print("Generating response...")
    response = generator(
        prompt,
        max_length=MAX_RESPONSE,
        truncation=True,
        num_return_sequences=1,
        do_sample=True
    )
    generated_text = response[0]['generated_text']
    return generated_text