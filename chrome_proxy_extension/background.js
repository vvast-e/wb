// background.js для manifest_version 3
chrome.runtime.onInstalled.addListener(() => {
    chrome.proxy.settings.set(
        {
            value: {
                mode: "fixed_servers",
                rules: {
                    singleProxy: {
                        scheme: "http",
                        host: "p15184.ltespace.net",
                        port: 15184
                    },
                    bypassList: ["localhost"]
                }
            },
            scope: "regular"
        },
        function () { }
    );
});

chrome.webRequest.onAuthRequired.addListener(
    function (details) {
        return {
            authCredentials: {
                username: "uek7t66y",
                password: "zbygddap"
            }
        };
    },
    { urls: ["<all_urls>"] },
    ["blocking"]
);