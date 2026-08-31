if (process.env.COOKIE) {
  this.cookieJar = process.env.COOKIE;
}

this.client = axios.create({
  baseURL: this.baseUrl,
  headers: {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "User-Agent":
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Origin": "https://agents.texas4win.com",
    "Referer": "https://agents.texas4win.com/",
  },
  timeout: 30000,
  withCredentials: true,
});

// استخراج الكوكيز الجديدة من كل رد وتحديث الـ Jar
this.client.interceptors.response.use(
  (response) => {
    const setCookie = response.headers["set-cookie"];
    if (setCookie && Array.isArray(setCookie)) {
      const newCookies = setCookie.map((c) => c.split(";")[0]).join("; ");
      this.cookieJar = this.cookieJar ? `${this.cookieJar}; ${newCookies}` : newCookies;
    }
    return response;
  },
  (error) => {
    const setCookie = error.response?.headers?.["set-cookie"];
    if (setCookie && Array.isArray(setCookie)) {
      const newCookies = setCookie.map((c) => c.split(";")[0]).join("; ");
      this.cookieJar = this.cookieJar ? `${this.cookieJar}; ${newCookies}` : newCookies;
    }
    return Promise.reject(error);
  }
);

// إرفاق الكوكيز مع كل طلب
this.client.interceptors.request.use((config) => {
  if (this.cookieJar) {
    config.headers["Cookie"] = this.cookieJar;
  }
  return config;
});
