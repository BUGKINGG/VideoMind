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

    /**
     * 从B站URL中提取BV号
     * 支持格式: https://www.bilibili.com/video/BV1xxxxx / https://b23.tv/BV1xxxxx
     */
    public static String extractBvid(String rawUrl) {
        if (rawUrl == null || rawUrl.isEmpty()) {
            return null;
        }
        String baseUrl = extractBaseUrl(rawUrl);
        // 匹配 /BV 开头的一段
        int bvIdx = baseUrl.toUpperCase().indexOf("/BV");
        if (bvIdx > 0) {
            String afterBv = baseUrl.substring(bvIdx + 1);
            // BV号通常是10位，如 BV1xx411c7mD
            int endIdx = 0;
            for (int i = 0; i < afterBv.length(); i++) {
                char c = afterBv.charAt(i);
                if (Character.isLetterOrDigit(c)) {
                    endIdx = i + 1;
                } else {
                    break;
                }
            }
            if (endIdx > 2) {
                return afterBv.substring(0, endIdx);
            }
        }
        return null;
    }
}
