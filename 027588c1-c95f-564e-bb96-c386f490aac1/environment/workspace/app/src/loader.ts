export async function loadConfig(): Promise<{ name: string; ready: boolean; seed: number }> {
  return { name: "@pkg/dual", ready: true, seed: 42 };
}
