var config = {
    mode: "fixed_servers",
    rules: {
        singleProxy: {
            scheme: "https", // или "http"
            host: "p15184.ltespace.net",
            port: parseInt(15184)
        },
        bypassList: ["localhost"]
    }
};
chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
function callbackFn(details) {
    return {
        authCredentials: {
            username: "uek7t66y",
            password: "zbygddap"
        }
    };
}
chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    {urls: ["<all_urls>"]},
    ['blocking']
);