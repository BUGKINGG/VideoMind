package com.example.backend.common;

public class BilibiliUrlUtils {

    /**
     * 提取纯净URL（去掉 ? 及后面所有参数）
     */
    public static String extractBaseUrl(String rawUrl) {
        if (rawUrl == null || rawUrl.isEmpty()) {
            return rawUrl;
        }
        // 去掉锚点 #
        int hashIdx = rawUrl.indexOf('#');
        String url = hashIdx > 0 ? rawUrl.substring(0, hashIdx) : rawUrl;

        // 去掉 query string
        int queryIdx = url.indexOf('?');
        return queryIdx > 0 ? url.substring(0, queryIdx) : url;
    }

    /**
     * 提取分P序号，默认1
     */
    public static Integer extractPart(String rawUrl) {
        if (rawUrl == null || !rawUrl.contains("?")) {
            return 1;
        }
        String query = rawUrl.substring(rawUrl.indexOf('?') + 1);
        for (String param : query.split("&")) {
            if (param.startsWith("p=")) {
                try {
                    return Integer.parseInt(param.substring(2));
                } catch (NumberFormatException e) {
                    return 1;
                }
            }
        }
        return 1;
    }
}
