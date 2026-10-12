export async function api(path: string, data?: unknown) {
  const csrf =
    document.cookie
      .split("; ")
      .find((x) => x.startsWith("csrftoken="))
      ?.split("=")[1] || "";
  const response = await fetch("/api" + path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
    ...(data === undefined
      ? {}
      : { method: "POST", body: JSON.stringify(data) }),
  });
  const body = response.headers
    .get("content-type")
    ?.includes("application/json")
    ? await response.json()
    : {
        detail:
          "The server rejected this request. Refresh your session and retry.",
      };
  if (!response.ok)
    throw new Error(
      typeof body.detail === "string" ? body.detail : JSON.stringify(body),
    );
  return body;
}
