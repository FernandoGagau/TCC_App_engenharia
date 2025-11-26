
Logo
Search
/

Ask AI
API
Models
Chat
Ranking
Login

Overview
Quickstart
FAQ
Principles
Models
Enterprise
Features
Privacy and Logging
Zero Data Retention (ZDR)
Model Routing
Provider Routing
Latency and Performance
Presets
Prompt Caching
Structured Outputs
Tool Calling

Multimodal
Message Transforms
Uptime Optimization
Web Search
Zero Completion Insurance
Provisioning API Keys
App Attribution
API Reference
Overview
Streaming
Limits
Authentication
Parameters
Errors

Responses API Alpha
POST
Completion
POST
Chat completion
GET
Get a generation
GET
List available models
GET
List endpoints for a model
GET
List models filtered by user provider preferences
GET
List available providers
GET
Get credits
POST
Create a Coinbase charge

Analytics
GET
Get Activity

Authentication

API Keys
Use Cases
BYOK
Crypto API
OAuth PKCE
MCP Servers
Organization Management
For Providers
Reasoning Tokens
Usage Accounting
User Tracking
Community
Frameworks and Integrations Overview
Effect AI SDK
LangChain
Langfuse
Mastra
OpenAI SDK
PydanticAI
Vercel AI SDK
Xcode
Zapier
Discord
API Reference
Chat completion
POST
https://openrouter.ai/api/v1/chat/completions
POST
/api/v1/chat/completions

Python

import requests
url = "https://openrouter.ai/api/v1/chat/completions"
payload = {
    "model": "openai/gpt-3.5-turbo",
    "messages": [
        {
            "role": "user",
            "content": "What is the meaning of life?"
        }
    ]
}
headers = {
    "Authorization": "Bearer <token>",
    "Content-Type": "application/json"
}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
Try it
200
Successful

{
  "id": "gen-12345",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "The meaning of life is a complex and subjective question...",
        "refusal": ""
      },
      "logprobs": {},
      "finish_reason": "stop",
      "index": 0
    }
  ],
  "provider": "OpenAI",
  "model": "openai/gpt-3.5-turbo",
  "object": "chat.completion",
  "created": 1735317796,
  "system_fingerprint": {},
  "usage": {
    "prompt_tokens": 14,
    "completion_tokens": 163,
    "total_tokens": 177
  }
}
Send a chat completion request to a selected model. The request must contain a "messages" array. All advanced options from the base request are also supported.
Headers
Authorization
string
Required
Bearer authentication of the form Bearer <token>, where token is your auth token.

Request
This endpoint expects an object.
model
string
Required
The model ID to use. If unspecified, the user's default is used.
messages
list of objects
Required

Hide 2 properties
role
enum
Required
Allowed values:
system
developer
user
assistant
tool
content
string
Required
models
list of strings
Optional
Alternate list of models for routing overrides.
provider
object
Optional
Preferences for provider routing.

Show 1 properties
reasoning
object
Optional
Configuration for model reasoning/thinking tokens


Show 3 properties
usage
object
Optional
Whether to include usage information in the response

Show 1 properties
transforms
list of strings
Optional
List of prompt transforms (OpenRouter-only).

stream
boolean
Optional
Defaults to false
Enable streaming of results.
max_tokens
integer
Optional
Maximum number of tokens (range: [1, context_length)).

temperature
double
Optional
Sampling temperature (range: [0, 2]).

seed
integer
Optional
Seed for deterministic outputs.
top_p
double
Optional
Top-p sampling value (range: (0, 1]).

top_k
integer
Optional
Top-k sampling value (range: [1, Infinity)).

frequency_penalty
double
Optional
Frequency penalty (range: [-2, 2]).

presence_penalty
double
Optional
Presence penalty (range: [-2, 2]).

repetition_penalty
double
Optional
Repetition penalty (range: (0, 2]).

logit_bias
map from strings to doubles
Optional
Mapping of token IDs to bias values.
top_logprobs
integer
Optional
Number of top log probabilities to return.
min_p
double
Optional
Minimum probability threshold (range: [0, 1]).

top_a
double
Optional
Alternate top sampling parameter (range: [0, 1]).

user
string
Optional
A stable identifier for your end-users. Used to help detect and prevent abuse.

Response
Successful completion
id
string or null
choices
list of objects or null

Show 1 properties
Was this page helpful?
Yes
No
Previous
Get a generation
Next
Built with
Ask AI



Chat completion | OpenRouter | Documentation