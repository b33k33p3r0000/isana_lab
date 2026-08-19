// Domain cutover 2026-08-19: isana.io is the canonical host. Every other
// attached hostname (quantwhale.net, www.quantwhale.net, www.isana.io) 301s
// to it with path + query preserved. `run_worker_first` in wrangler.jsonc
// routes every request through this handler, so the redirect wins even when
// the path matches an asset.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname !== "isana.io") {
      url.hostname = "isana.io";
      return Response.redirect(url.toString(), 301);
    }
    return env.ASSETS.fetch(request);
  },
};
