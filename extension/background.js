chrome.browserAction.onClicked.addListener(function(tab) {
  // 在这里修改你想跳转的网址
  chrome.tabs.create({ url: 'http://127.0.0.1:5000/' });
}); 