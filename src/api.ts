export default {
  async fetch(request) {
    const url = new URL(request.url);
    url.hostname = "agents.texas4win.com";
    url.protocol = "https:";

    const headers = new Headers(request.headers);
    headers.set("Host", "agents.texas4win.com");
    headers.set("Origin", "https://agents.texas4win.com");
    headers.set("Referer", "https://agents.texas4win.com/");
    headers.set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36");

    let bodyData = null;
    if (request.method !== "GET" && request.method !== "HEAD") {
      bodyData = await request.arrayBuffer();
    }

    const newRequest = new Request(url.toString(), {
      method: request.method,
      headers: headers,
      body: bodyData,
      redirect: "follow"
    });

    const response = await fetch(newRequest);
    return new Response(response.body, response);
  }
};
