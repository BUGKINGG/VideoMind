package com.example.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.backend.entity.Subtitle;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface SubtitleMapper extends BaseMapper<Subtitle> {
    /**
     * 批量插入弹幕数据
     * @param list
     */
    void insertBatch(@Param("list") List<Subtitle> list);
}
