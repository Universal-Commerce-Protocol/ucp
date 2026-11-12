/**
 * Model providers. The assistant only needs one thing from a model: stream a
 * chat completion for a list of messages. Two adapters cover self-hosted and
 * Cloudflare-hosted open-weight models:
 *
 *  - "openai-compatible": any server speaking the OpenAI chat-completions
 *    protocol: vLLM, Ollama, TGI, llama.cpp server, LM Studio, SGLang, or a
 *    hosted open-model API. This is what a self-hosted or fine-tuned model
 *    will expose.
 *  - "workers-ai": Cloudflare Workers AI (open models such as Llama, Qwen,
 *    Mistral, Gemma) through the `AI` binding; no GPU to run.
 */

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface GenerateOptions {
  maxTokens: number;
  temperature: number;
  signal?: AbortSignal;
}

export type FinishReason = "stop" | "length" | "unknown";

export interface ModelProvider {
  readonly name: string;
  stream(
    messages: ChatMessage[],
    onDelta: (text: string) => void,
    opts: GenerateOptions
  ): Promise<FinishReason>;
}

/** Minimal shape of the Workers AI binding we rely on (keeps us independent of type package versions). */
export interface WorkersAiBinding {
  run(model: string, input: Record<string, unknown>): Promise<unknown>;
}

export class ProviderError extends Error {
  constructor(
    message: string,
    readonly status?: number
  ) {
    super(message);
  }
}

/* ------------------------------------------------------------ OpenAI-compatible */

export class OpenAICompatibleProvider implements ModelProvider {
  readonly name: string;
  constructor(
    private readonly baseUrl: string,
    private readonly model: string,
    private readonly apiKey?: string
  ) {
    this.name = `openai-compatible:${model}`;
  }

  async stream(
    messages: ChatMessage[],
    onDelta: (text: string) => void,
    opts: GenerateOptions
  ): Promise<FinishReason> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.apiKey) headers.Authorization = `Bearer ${this.apiKey}`;
    const res = await fetch(
      `${this.baseUrl.replace(/\/+$/, "")}/chat/completions`,
      {
        method: "POST",
        headers,
        signal: opts.signal,
        body: JSON.stringify({
          model: this.model,
          messages,
          stream: true,
          max_tokens: opts.maxTokens,
          temperature: opts.temperature,
        }),
      }
    );
    if (!res.ok || !res.body) {
      throw new ProviderError(
        `model server returned ${res.status}`,
        res.status
      );
    }
    let finish: FinishReason = "unknown";
    for await (const data of sseData(res.body)) {
      if (data === "[DONE]") break;
      let json: {
        choices?: {
          delta?: { content?: string | null };
          finish_reason?: string | null;
        }[];
      };
      try {
        json = JSON.parse(data);
      } catch {
        continue;
      }
      const choice = json.choices?.[0];
      if (!choice) continue;
      if (choice.delta?.content) onDelta(choice.delta.content);
      if (choice.finish_reason)
        finish = choice.finish_reason === "length" ? "length" : "stop";
    }
    return finish;
  }
}

/* ------------------------------------------------------------------ Workers AI */

export class WorkersAiProvider implements ModelProvider {
  readonly name: string;
  constructor(
    private readonly ai: WorkersAiBinding,
    private readonly model: string
  ) {
    this.name = `workers-ai:${model}`;
  }

  async stream(
    messages: ChatMessage[],
    onDelta: (text: string) => void,
    opts: GenerateOptions
  ): Promise<FinishReason> {
    const out = await this.ai.run(this.model, {
      messages,
      stream: true,
      max_tokens: opts.maxTokens,
      temperature: opts.temperature,
    });
    if (!(out instanceof ReadableStream)) {
      // Some models ignore `stream`; fall back to the whole response.
      const text = (out as { response?: string })?.response ?? "";
      if (text) onDelta(text);
      return "unknown";
    }
    let finish: FinishReason = "unknown";
    for await (const data of sseData(out)) {
      if (data === "[DONE]") break;
      let json: { response?: string; usage?: unknown };
      try {
        json = JSON.parse(data);
      } catch {
        continue;
      }
      if (json.response) onDelta(json.response);
      if (json.usage) finish = "stop";
    }
    return finish;
  }
}

/* ------------------------------------------------------------------- factory */

export interface ProviderEnv {
  MODEL_PROVIDER?: string;
  MODEL: string;
  MODEL_BASE_URL?: string;
  MODEL_API_KEY?: string;
  AI?: WorkersAiBinding;
}

export function createProvider(env: ProviderEnv): ModelProvider {
  const kind = (env.MODEL_PROVIDER ?? "openai-compatible").toLowerCase();
  if (kind === "workers-ai") {
    if (!env.AI)
      throw new ProviderError(
        "MODEL_PROVIDER=workers-ai requires the AI binding in wrangler.toml"
      );
    return new WorkersAiProvider(env.AI, env.MODEL);
  }
  if (kind === "openai-compatible") {
    if (!env.MODEL_BASE_URL)
      throw new ProviderError(
        "MODEL_BASE_URL is required for the openai-compatible provider"
      );
    return new OpenAICompatibleProvider(
      env.MODEL_BASE_URL,
      env.MODEL,
      env.MODEL_API_KEY
    );
  }
  throw new ProviderError(`unknown MODEL_PROVIDER: ${kind}`);
}

/* ---------------------------------------------------------------------- utils */

/** Yield the `data:` payload of each server-sent event in a byte stream. */
export async function* sseData(
  body: ReadableStream<Uint8Array>
): AsyncGenerator<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    let idx = buffer.indexOf("\n\n");
    while (idx >= 0) {
      const frame = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const data = frame
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trim())
        .join("\n");
      if (data) yield data;
      idx = buffer.indexOf("\n\n");
    }
    if (done) break;
  }
}
