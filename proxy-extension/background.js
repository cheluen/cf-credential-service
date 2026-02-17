chrome.webRequest.onAuthRequired.addListener(
  function(details, callbackFn) {
    const url = new URL(details.url);
    const proxyHost = PROXY_HOST;
    const proxyPort = PROXY_PORT;
    const username = PROXY_USER;
    const password = PROXY_PASS;
    
    if (details.challenger.host === proxyHost && details.challenger.port === proxyPort) {
      callbackFn({
        authCredentials: {
          username: username,
          password: password
        }
      });
    } else {
      callbackFn({});
    }
  },
  {urls: ["<all_urls>"]},
  ['asyncBlocking']
);
