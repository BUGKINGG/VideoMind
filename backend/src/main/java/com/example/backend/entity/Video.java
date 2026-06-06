package com.example.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("video")
public class Video {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String url;

    private Long userId;

    private String title;

    // 状态，0为解析中，1为完成，2为失败
    private Integer status;

    // ai视频总结的内容，如果已经总结过了，直接拿出来用就好
    private String summary;

    // 集数。同一个BV号下可能分了很多集，默认从1开始
    private Integer part;

    @TableField("created_at")
    private LocalDateTime createAt;

    @TableField("subtitle_count")
    private Integer subtitleCount;
}
