package com.example.backend.service.serviceImpl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.backend.common.BaseContext;
import com.example.backend.common.BilibiliUrlUtils;
import com.example.backend.dto.LoginDTO;
import com.example.backend.dto.RegisterDTO;
import com.example.backend.entity.Conversation;
import com.example.backend.entity.Message;
import com.example.backend.entity.Video;
import com.example.backend.mapper.ConversationMapper;
import com.example.backend.mapper.MessageMapper;
import com.example.backend.mapper.UserMapper;
import com.example.backend.mapper.VideoMapper;
import com.example.backend.service.UserService;
import com.example.backend.entity.User;
import com.example.backend.vo.MessageVO;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;

@Service
public class UserServiceImpl extends ServiceImpl<UserMapper, User> implements UserService {

    @Autowired
    private BCryptPasswordEncoder bCryptPasswordEncoder;
    @Autowired
    private UserMapper userMapper;
    @Autowired
    private ConversationMapper conversationMapper;
    @Autowired
    private VideoMapper videoMapper;
    @Autowired
    private MessageMapper messageMapper;
    @Autowired
    private StringRedisTemplate redisTemplate;

    @Override
    public boolean register(RegisterDTO registerDTO) {
        QueryWrapper<User> wrapper = new QueryWrapper<>();

        // 判断手机号是否已经被注册
        // 利用mp在数据库中查询
        wrapper.eq("phone", registerDTO.getAccount());

        // count为符合记录的数量
        long count = this.count(wrapper);

        // 存在手机号，则返回false
        if(count > 0){
            return false;
        }

        User user = new User();
        BeanUtils.copyProperties(registerDTO, user);

        user.setPasswordHash(bCryptPasswordEncoder.encode(registerDTO.getPassword()));

        user.setCookie(null);
        user.setPhone(registerDTO.getAccount());
        user.setCreatedAt(LocalDateTime.now());
        user.setUpdatedAt(LocalDateTime.now());

        this.save(user);
        return true;
    }

    public User login(LoginDTO loginDTO){
        User tempUser = userMapper.selectOne(
            Wrappers.<User>lambdaQuery()
                .eq(User::getPhone, loginDTO.getAccount())
        );
        User user = new User();

        if(tempUser == null){
            return null;
        }

        boolean matches = bCryptPasswordEncoder.matches(loginDTO.getPassword(), tempUser.getPasswordHash());

        if(!matches){
            return null;
        }

        return tempUser;
    }

    public void updateCookie(String cookie){
        Long userId = BaseContext.getCurrentId();

        LambdaUpdateWrapper<User> wrapper = new LambdaUpdateWrapper<>();
        wrapper.eq(User::getId, userId)
            .set(User::getCookie, cookie);

        userMapper.update(null, wrapper);
    }

    @Override
    public void updateUsername(String username){
        Long userId = BaseContext.getCurrentId();

        LambdaUpdateWrapper<User> wrapper = new LambdaUpdateWrapper<>();
        wrapper.eq(User::getId, userId)
            .set(User::getUsername, username);

        userMapper.update(null, wrapper);
    }

    @Override
    public List<MessageVO> getList(){
        Long userId = BaseContext.getCurrentId();
        // 包含处理中(status=0)和已完成(status=1)，排除失败(status=2)
        List<Conversation> list = conversationMapper.selectList(
            Wrappers.<Conversation>lambdaQuery()
                .eq(Conversation::getUserId, userId)
                .in(Conversation::getStatus, Arrays.asList(0, 1))
                .orderByDesc(Conversation::getUpdatedAt)
        );
        return list.stream().map(conv -> {
            MessageVO vo = new MessageVO();
            BeanUtils.copyProperties(conv, vo);
            // 从 Video 表补充 bvid、part
            if (conv.getVideoId() != null) {
                Video video = videoMapper.selectById(conv.getVideoId());
                if (video != null) {
                    vo.setPart(video.getPart());
                    vo.setBvid(BilibiliUrlUtils.extractBvid(video.getUrl()));
                }
            }
            return vo;
        }).toList();
    }

    @Override
    public MessageVO getMessages(Long id){
        Conversation conversation = conversationMapper.selectOne(
            Wrappers.<Conversation>lambdaQuery()
                .eq(Conversation::getId, id)
        );
        MessageVO messageVO = new MessageVO();
        BeanUtils.copyProperties(conversation, messageVO);

        // 从 Video 表补充 bvid、part、url
        if (conversation != null && conversation.getVideoId() != null) {
            Video video = videoMapper.selectById(conversation.getVideoId());
            if (video != null) {
                messageVO.setPart(video.getPart());
                messageVO.setUrl(video.getUrl());
                messageVO.setBvid(BilibiliUrlUtils.extractBvid(video.getUrl()));
            }
        }

        // 处理中的对话：从 Redis 获取 sid，供前端重连 SSE（summary）
        if (conversation != null && conversation.getStatus() == 0) {
            String sid = redisTemplate.opsForValue()
                .get("videomind:sse:conv:" + id);
            messageVO.setSid(sid);
        }

        // 检查是否有进行中的 chat，供前端切回来时重连（chat）
        if (conversation != null) {
            String chatSid = redisTemplate.opsForValue()
                .get("videomind:sse:chat_pending:" + id);
            messageVO.setPendingChatSid(chatSid);
        }

        List<Message> list = messageMapper.selectList(
            Wrappers.<Message>lambdaQuery()
                .eq(Message::getConversationId, id)
                .orderByAsc(Message::getCreatedAt)
        );
        messageVO.setMessages(list);
        return messageVO;
    }
}
