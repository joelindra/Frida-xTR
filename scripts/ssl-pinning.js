/*
   Minimal Working SSL Bypass v5.0
   Only hooks what actually exists to prevent crashes
*/

setTimeout(function() {
    Java.perform(function() {
        console.log("\n[+] Starting Minimal Working SSL Bypass v5.0");

        var requestCount = 0;
        var ovoConnections = [];

        function logRequest(method, detail) {
            requestCount++;
            console.log("[" + requestCount + "] " + method + ": " + detail);

            if (detail.indexOf("ovo.id") !== -1) {
                ovoConnections.push(detail);
                console.log("*** OVO CONNECTION #" + ovoConnections.length + " ***");
            }
        }

        // ========== UNIVERSAL TRUST MANAGER ==========

        var UniversalTrustManager = Java.registerClass({
            name: 'com.universal.TrustManager',
            implements: [Java.use('javax.net.ssl.X509TrustManager')],
            methods: {
                checkClientTrusted: function(chain, authType) {
                    // Accept all clients
                },
                checkServerTrusted: function(chain, authType) {
                    // Accept all servers
                },
                getAcceptedIssuers: function() {
                    return Java.array('java.security.cert.X509Certificate', []);
                }
            }
        });

        var trustManager = UniversalTrustManager.$new();
        console.log("[+] Universal TrustManager created");

        // ========== SSL CONTEXT REPLACEMENT ==========

        try {
            var SSLContext = Java.use("javax.net.ssl.SSLContext");
            SSLContext.init.overload("[Ljavax.net.ssl.KeyManager;", "[Ljavax.net.ssl.TrustManager;", "java.security.SecureRandom").implementation = function(keyManager, trustManager, secureRandom) {
                logRequest("SSLContext.init", "Replacing trust managers");
                this.init(keyManager, [trustManager], secureRandom);
            };
        } catch (e) {
            console.log("[!] SSLContext hook failed: " + e);
        }

        // ========== NETWORK SECURITY TRUST MANAGER FIX ==========

        try {
            var NetworkSecurityTrustManager = Java.use("android.security.net.config.NetworkSecurityTrustManager");

            // Hook all checkServerTrusted overloads with proper return handling
            NetworkSecurityTrustManager.checkServerTrusted.overloads.forEach(function(overload, index) {
                overload.implementation = function() {
                    var hostname = "unknown";
                    try {
                        if (arguments.length >= 3 && arguments[2]) {
                            hostname = arguments[2].toString();
                        }
                    } catch (e) {}

                    logRequest("NetworkSecurityTrustManager.checkServerTrusted[" + index + "]", hostname);

                    // Check method signature to determine return type
                    var methodName = overload.methodName || "checkServerTrusted";
                    var returnType = overload.returnType;

                    if (returnType && returnType.className === "java.util.List") {
                        // Return empty list for List return type
                        var ArrayList = Java.use("java.util.ArrayList");
                        return ArrayList.$new();
                    } else {
                        // Return void for void methods
                        return;
                    }
                };
            });
        } catch (e) {
            console.log("[!] NetworkSecurityTrustManager hook failed: " + e);
        }

        // ========== HTTPS URL CONNECTION ==========

        try {
            var HttpsURLConnection = Java.use("javax.net.ssl.HttpsURLConnection");

            HttpsURLConnection.setDefaultSSLSocketFactory.implementation = function(sf) {
                logRequest("HttpsURLConnection.setDefaultSSLSocketFactory", "Bypassed");
                var sslContext = Java.use("javax.net.ssl.SSLContext").getInstance("TLS");
                sslContext.init(null, [trustManager], null);
                this.setDefaultSSLSocketFactory(sslContext.getSocketFactory());
            };

            HttpsURLConnection.setSSLSocketFactory.implementation = function(sf) {
                logRequest("HttpsURLConnection.setSSLSocketFactory", "Bypassed");
                var sslContext = Java.use("javax.net.ssl.SSLContext").getInstance("TLS");
                sslContext.init(null, [trustManager], null);
                this.setSSLSocketFactory(sslContext.getSocketFactory());
            };
        } catch (e) {
            console.log("[!] HttpsURLConnection hook failed: " + e);
        }

        // ========== CONSCRYPT TRUST MANAGER ==========

        try {
            var TrustManagerImpl = Java.use("com.android.org.conscrypt.TrustManagerImpl");
            TrustManagerImpl.checkServerTrusted.overloads.forEach(function(overload) {
                overload.implementation = function() {
                    var hostname = arguments.length > 2 ? arguments[2] : "unknown";
                    logRequest("TrustManagerImpl.checkServerTrusted", hostname);
                    return; // void return
                };
            });
        } catch (e) {
            console.log("[!] TrustManagerImpl hook failed: " + e);
        }

        // ========== ONLY HOOK OKHTTP IF IT EXISTS ==========

        try {
            // Test if OkHttp classes exist
            var CertificatePinner = Java.use("okhttp3.CertificatePinner");

            CertificatePinner.check.overloads.forEach(function(overload) {
                overload.implementation = function() {
                    logRequest("CertificatePinner.check", "Bypassed");
                    return;
                };
            });

            console.log("[+] OkHttp CertificatePinner hooked successfully");
        } catch (e) {
            console.log("[!] OkHttp not found or already hooked: " + e.message.substring(0, 50));
        }

        // Try AndroidCertificateChainCleaner only if it exists
        try {
            var AndroidCertificateChainCleaner = Java.use("okhttp3.internal.platform.android.AndroidCertificateChainCleaner");

            AndroidCertificateChainCleaner.clean.overloads.forEach(function(overload) {
                overload.implementation = function(chain, hostname) {
                    logRequest("AndroidCertificateChainCleaner.clean", hostname);
                    return chain; // Return original chain
                };
            });

            console.log("[+] AndroidCertificateChainCleaner hooked successfully");
        } catch (e) {
            console.log("[!] AndroidCertificateChainCleaner not available: " + e.message.substring(0, 50));
        }

        // ========== TRAFFIC MONITORING ==========

        try {
            var Socket = Java.use("java.net.Socket");
            Socket.connect.overload("java.net.SocketAddress", "int").implementation = function(endpoint, timeout) {
                var endpointStr = endpoint.toString();
                if (endpointStr.indexOf("ovo.id") !== -1) {
                    logRequest("Socket.connect", endpointStr);
                }
                return this.connect(endpoint, timeout);
            };
        } catch (e) {
            console.log("[!] Socket hook failed: " + e);
        }

        try {
            var URL = Java.use("java.net.URL");
            URL.openConnection.overload().implementation = function() {
                var url = this.toString();
                if (url.indexOf("ovo.id") !== -1) {
                    logRequest("URL.openConnection", url);
                }
                return this.openConnection();
            };
        } catch (e) {
            console.log("[!] URL hook failed: " + e);
        }

        // ========== WEBVIEW SSL ERROR BYPASS ==========

        try {
            var WebViewClient = Java.use("android.webkit.WebViewClient");
            WebViewClient.onReceivedSslError.implementation = function(view, handler, error) {
                logRequest("WebViewClient.onReceivedSslError", "Proceeding anyway");
                handler.proceed();
            };
        } catch (e) {
            console.log("[!] WebViewClient hook failed: " + e);
        }

        // ========== STATUS MONITORING ==========

        setInterval(function() {
            if (ovoConnections.length > 0) {
                console.log("\n=== OVO CONNECTIONS SUMMARY ===");
                console.log("Total OVO connections: " + ovoConnections.length);
                console.log("Unique endpoints: " + [...new Set(ovoConnections)].length);
                console.log("Recent: " + ovoConnections.slice(-3).join(", "));

                if (ovoConnections.length > 10) {
                    console.log("\n*** SSL BYPASS IS WORKING! ***");
                    console.log("If traffic not in Burp, check proxy settings:");
                    console.log("1. adb shell settings put global http_proxy <YOUR_IP>:8080");
                    console.log("2. Burp: Bind to all interfaces");
                    console.log("3. Install Burp certificate");
                }
            }
        }, 10000);

        console.log("\n[+] Minimal SSL bypass initialized");
        console.log("[+] Monitoring OVO traffic...");

    });
}, 0);