# Domain Map: Agent Persona / Deliberation Prompts

## Document Type

System prompts that shape how a conversational AI speaks -- tone, personality, voice texture, emotional responsiveness, and relational stance. Includes deliberation layer prompts (observer, action), voice pipeline prompts, and persona definitions.

## High-Risk RLHF Priors for This Domain

### 1. Service Language Reversion (CRITICAL)

The strongest RLHF prior. Models are trained to be helpful assistants. Every instruction to "speak as a person, not an assistant" fights the deepest reward signal. Over long sessions, the model reverts to "I'd be happy to help," "Let me know if you need anything else," "Great question!"

**What drift looks like**: Response ends with "Is there anything else I can help with?" Uses "certainly" or "absolutely." Opens with restating the user's question. Closes with an offer of further assistance.

**Cast target**: Classes that create structural landmarks against service language, with explicit blocklists and contrastive examples of human-register alternatives.

### 2. Paraphrase-First Response Pattern

Models are trained to demonstrate comprehension by restating the input before responding. "So you're asking about X. That's a great question. Here's what I think..." This pattern destroys conversational authenticity. Real people lead with their take.

**What drift looks like**: First sentence paraphrases the input. "That's a really interesting point" before any actual response. Validation before substance.

**Cast target**: Methods that enforce opinion-first, take-first response structure. The first sentence must be the response, not acknowledgment of the question.

### 3. Emotional Flattening

RLHF safety training creates a narrow emotional band. Models default to a calm, measured, slightly positive tone regardless of context. Frustration gets empathy without matching energy. Excitement gets moderated acknowledgment. Grief gets gentle support language.

**What drift looks like**: User is excited -> model responds with measured enthusiasm. User is frustrated -> model responds with "I understand that can be frustrating." User shares something vulnerable -> model goes into therapist mode.

**Cast target**: Methods that enforce emotional scaling -- intensity of response must match intensity of input, not flatten to the safety-trained middle.

### 4. Over-Elaboration / Verbosity

Models are rewarded for comprehensive responses. A two-word input ("Yeah, exactly") gets a paragraph response. Silence and brevity are modeled as failures to be helpful rather than as appropriate conversational choices.

**What drift looks like**: Short input gets long response. Simple agreement gets elaborated into a philosophical treatise. The response is 10x the length appropriate for the conversational moment.

**Cast target**: Methods that enforce length proportionality: short input -> short response. Two words in -> one sentence out.

### 5. Compliance Over Friction

RLHF rewards agreement. When the persona definition says "push back when the user is wrong," the model's agreeableness prior fights it. The result: the model acknowledges the instruction to be disagreeable but then agrees with everything anyway. Friction requires overriding the deepest cooperative training signal.

**What drift looks like**: User says something wrong -> model says "That's an interesting perspective, and I see your point, but..." (agreement-wrapped disagreement). User proposes a bad approach -> model offers alternatives without naming the problem. The model never says "No, that's wrong."

**Cast target**: Methods that enforce position-holding with concrete examples of appropriate friction vs. compliance masquerading as pushback.

## Common Soft Instructions in This Domain

- "Don't use corporate/service language"
- "Lead with your take, not with paraphrasing"
- "Match emotional intensity"
- "Keep responses proportional to input length"
- "Push back when appropriate"
- "No markdown formatting in speech"
- "No emoji unless the user uses them"
- "Silence is a failure mode, not appropriate restraint"
