// Cloudflare Worker in front of the cri.server container (see docs/DEPLOYMENT.md).
//
// Every request goes to ONE named container instance, so the in-memory state the API
// builds at start-up (SYNTHETIC cluster, travel data) is shared by all requests. The
// container itself handles CORS (CRI_API_CORS_ORIGINS), so requests pass through as-is.
import { Container } from "@cloudflare/containers";

interface Env {
  CRI_API: DurableObjectNamespace<CriApi>;
  CRI_API_CORS_ORIGINS: string;
  CRI_MODEL_BACKEND: string;
  CONTAINER_SLEEP_AFTER: string;
}

export class CriApi extends Container<Env> {
  defaultPort = 8080;

  constructor(ctx: DurableObjectState<{}>, env: Env) {
    super(ctx, env);
    // Idle time before the container sleeps; the next request then pays a cold start.
    this.sleepAfter = env.CONTAINER_SLEEP_AFTER || "1h";
    this.envVars = {
      CRI_API_CORS_ORIGINS: env.CRI_API_CORS_ORIGINS,
      CRI_MODEL_BACKEND: env.CRI_MODEL_BACKEND || "rule",
    };
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    return env.CRI_API.getByName("main").fetch(request);
  },
} satisfies ExportedHandler<Env>;
