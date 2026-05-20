import type { ChatSettings, UsageMetadata } from "@/types/chat";

interface GroqResponse {
  content: string;
  usage: UsageMetadata;
}

interface AskGroqParams {
  prompt: string;
  settings: ChatSettings;
}

function randomInRange(min: number, max: number) {
  return Math.random() * (max - min) + min;
}

export async function askGroqSimulation({ prompt, settings }: AskGroqParams): Promise<GroqResponse> {
  const promptTokens = Math.max(16, Math.round(prompt.length / 3.5));
  const completionTokens = Math.round(promptTokens * randomInRange(1.6, 2.5));
  const latencySeconds = Number(randomInRange(0.24, 1.15).toFixed(2));

  await new Promise((resolve) => {
    setTimeout(resolve, Math.round(latencySeconds * 1000));
  });

  const model = "llama-3.3-70b-versatile";
  const content = settings.jsonMode
    ? JSON.stringify(
        {
          summary: "Respuesta generada por Groq en modo JSON.",
          model,
          guidance: "La estrategia recomendada es iterar en pequeños lotes, observando coste de tokens por turno.",
          controls: {
            temperature: settings.temperature,
            top_p: settings.topP,
            json_mode: settings.jsonMode,
          },
        },
        null,
        2,
      )
    : `Modelo ${model}: para tu consulta \"${prompt.slice(0, 120)}\", propongo un plan en 3 pasos: 1) definir objetivo y constraints, 2) ejecutar una primera versión medible, 3) optimizar según latencia/tokens.`;

  return {
    content,
    usage: {
      promptTokens,
      completionTokens,
      totalTokens: promptTokens + completionTokens,
      latencySeconds,
      model,
    },
  };
}
