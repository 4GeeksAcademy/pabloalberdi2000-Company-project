import { NextRequest, NextResponse } from "next/server";

const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
const DEFAULT_MODEL = "llama-3.3-70b-versatile";

type InputMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

type ChatRequestBody = {
  messages: InputMessage[];
  temperature?: number;
  top_p?: number;
  json_mode?: boolean;
  stream?: boolean;
};

export async function POST(request: NextRequest) {
  const apiKey = process.env.GROQ_API_KEY;
  const model = process.env.GROQ_MODEL?.trim() || DEFAULT_MODEL;
  if (!apiKey) {
    return NextResponse.json({ error: "Missing GROQ_API_KEY in server environment." }, { status: 500 });
  }

  let body: ChatRequestBody;

  try {
    body = (await request.json()) as ChatRequestBody;
  } catch {
    return NextResponse.json({ error: "Invalid JSON payload." }, { status: 400 });
  }

  if (!Array.isArray(body.messages) || body.messages.length === 0) {
    return NextResponse.json({ error: "Field 'messages' is required." }, { status: 400 });
  }

  const payload: Record<string, unknown> = {
    model,
    messages: body.messages,
    temperature: body.temperature ?? 0.7,
    top_p: body.top_p ?? 0.9,
    stream: Boolean(body.stream),
  };

  if (body.json_mode) {
    payload.response_format = { type: "json_object" };
  }

  try {
    const upstream = await fetch(GROQ_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    if (!upstream.ok) {
      if (upstream.status === 401) {
        return NextResponse.json({ error: "Unauthorized: invalid Groq API key." }, { status: 401 });
      }

      const upstreamText = await upstream.text();
      return NextResponse.json(
        { error: `Groq upstream error (${upstream.status}): ${upstreamText || "Unknown error"}` },
        { status: 500 },
      );
    }

    if (body.stream) {
      return new Response(upstream.body, {
        status: 200,
        headers: {
          "Content-Type": upstream.headers.get("content-type") ?? "text/event-stream",
          "Cache-Control": "no-cache, no-transform",
          Connection: "keep-alive",
        },
      });
    }

    const data = (await upstream.json()) as {
      choices?: Array<{ message?: { content?: string } }>;
      usage?: {
        prompt_tokens?: number;
        completion_tokens?: number;
        total_tokens?: number;
      };
      model?: string;
    };

    const content = data.choices?.[0]?.message?.content ?? "";

    return NextResponse.json({
      content,
      model: data.model ?? model,
      usage: {
        prompt_tokens: data.usage?.prompt_tokens ?? 0,
        completion_tokens: data.usage?.completion_tokens ?? 0,
        total_tokens: data.usage?.total_tokens ?? 0,
      },
    });
  } catch {
    return NextResponse.json({ error: "Unexpected server error while contacting Groq." }, { status: 500 });
  }
}
