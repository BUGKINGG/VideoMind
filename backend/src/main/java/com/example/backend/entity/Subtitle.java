package com.example.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("subtitle")
public class Subtitle {
    @TableId(type = IdType.AUTO)
    private Long id;

    private Long videoId;

    private String content;

    private Double startAt;
    private Double endAt;

}
