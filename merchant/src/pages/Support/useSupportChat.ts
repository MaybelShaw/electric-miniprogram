import { useState, useEffect, useRef } from 'react';
import { message } from 'antd';
import { getChatMessages, sendChatMessage } from '@/services/api';
import type { SupportMessage } from '@/services/types';
import { getUser } from '@/utils/auth';

export interface ExtendedSupportMessage extends SupportMessage {
  local_id?: string;
  status?: 'sending' | 'sent' | 'error';
}

interface OfflineMessage {
  content: string;
  tempId: string;
  timestamp: number;
}

export function useSupportChat(userId: number | null, ticketId: number | null = null) {
  const [messages, setMessages] = useState<ExtendedSupportMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastFetchedAt, setLastFetchedAt] = useState<string | null>(null);
  const pollingRef = useRef<any>();
  const user = getUser();

  // Load from cache on mount/user change
  useEffect(() => {
    if (!userId) {
      setMessages([]);
      return;
    }

    const cacheKey = ticketId ? `chat_messages_ticket_${ticketId}` : `chat_messages_user_${userId}`;
    const cachedData = localStorage.getItem(cacheKey);
    let initialMessages: ExtendedSupportMessage[] = [];
    let initialLastFetchedAt = null;

    if (cachedData) {
      try {
        const parsed = JSON.parse(cachedData);
        initialMessages = parsed.messages || [];
        initialLastFetchedAt = parsed.lastFetchedAt || null;
        setMessages(initialMessages);
        setLastFetchedAt(initialLastFetchedAt);
      } catch (e) {
        console.error('Failed to parse cached messages', e);
      }
    } else {
      setMessages([]);
      setLastFetchedAt(null);
      setLoading(true);
    }

    // Initial fetch
    fetchMessages(userId, initialLastFetchedAt, true);
    
    return () => stopPolling();
  }, [userId]);

  // Polling effect
  useEffect(() => {
    if (!userId) return;
    startPolling();
    return () => stopPolling();
  }, [userId, lastFetchedAt]);

  const startPolling = () => {
    stopPolling();
    pollingRef.current = setInterval(() => {
      fetchMessages(userId, lastFetchedAt);
    }, 3000);
  };

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = undefined;
    }
  };

  const fetchMessages = async (uid: number | null, after: string | null, isInitial = false) => {
    if (!uid) return;
    try {
      const params: any = {};
      if (after) {
        params.after = after;
      }
      if (ticketId) {
        params.ticket_id = ticketId;
      }
      
      const res: any = await getChatMessages(uid, params);
      
      if (res && Array.isArray(res) && res.length > 0) {
        setMessages(prev => {
          const newMsgs = [...prev];
          res.forEach((msg: SupportMessage) => {
            // Check if message already exists (by id or by matching content/time for temp messages?)
            // For now just by ID. Temp messages will be handled in sendMessage
            if (!newMsgs.some(m => m.id === msg.id)) {
              newMsgs.push({ ...msg, status: 'sent' });
            }
          });
          
          // Sort by created_at
          newMsgs.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
          
          // Update cache
          if (newMsgs.length > 0) {
            const lastMsg = newMsgs[newMsgs.length - 1];
            // Only update lastFetchedAt if it's newer
            // But we need to be careful about out-of-order delivery if any? 
            // order_by('created_at') in backend handles this.
            const newLastFetchedAt = lastMsg.created_at;
            
            const storageKey = ticketId ? `chat_messages_ticket_${ticketId}` : `chat_messages_user_${uid}`;
            localStorage.setItem(storageKey, JSON.stringify({
              messages: newMsgs,
              lastFetchedAt: newLastFetchedAt
            }));
            
            // If we are in a render cycle, we can't set state for lastFetchedAt immediately if this is called from effect?
            // Actually this is async, so it's fine.
            if (after !== newLastFetchedAt) {
                setLastFetchedAt(newLastFetchedAt);
            }
          }
          return newMsgs;
        });
      }
    } catch (error) {
      console.error('Polling error:', error);
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  const sendMessage = async (
    content: string, 
    attachment?: File, 
    attachmentType?: 'image' | 'video', 
    extra?: { order_id?: number, product_id?: number, template_id?: number },
    optimisticInfo?: { order_info?: any, product_info?: any, template_info?: { content?: string, title?: string, content_type?: 'text' | 'card' | 'quick_buttons', content_payload?: Record<string, any> } }
  ) => {
    if (!userId || (!content.trim() && !attachment && !extra)) return;
    
    const templateContent = optimisticInfo?.template_info?.content || optimisticInfo?.template_info?.title || '';
    const tempId = `temp_${Date.now()}`;
    const tempMsg: ExtendedSupportMessage = {
      id: -1, // Placeholder
      conversation: 0,
      ticket: 0, // No longer tied to specific ticket ID on client side for chat display
      sender: user?.id || 0,
      sender_username: user?.username || 'Me',
      role: user?.role || 'user',
      content: content || templateContent || (attachmentType === 'image' ? '[图片]' : (attachmentType === 'video' ? '[视频]' : (extra?.product_id ? '[商品]' : (extra?.order_id ? '[订单]' : '')))),
      content_type: optimisticInfo?.template_info?.content_type,
      content_payload: optimisticInfo?.template_info?.content_payload,
      attachment_url: attachment ? URL.createObjectURL(attachment) : undefined,
      attachment_type: attachmentType,
      created_at: new Date().toISOString(),
      local_id: tempId,
      status: 'sending',
      order_info: optimisticInfo?.order_info,
      product_info: optimisticInfo?.product_info
    };

    // Optimistic update
    setMessages(prev => [...prev, tempMsg]);

    try {
      const res: any = await sendChatMessage(userId, content, attachment, attachmentType, { ...extra, ticket_id: ticketId || undefined });
      // Success
      setMessages(prev => {
        const newMsgs = prev.map(m => 
          m.local_id === tempId ? { ...res, status: 'sent' } : m
        );
        // Update cache immediately
         const lastMsg = newMsgs[newMsgs.length - 1];
         if (lastMsg) {
            const storageKey = ticketId ? `chat_messages_ticket_${ticketId}` : `chat_messages_user_${userId}`;
            localStorage.setItem(storageKey, JSON.stringify({
              messages: newMsgs,
              lastFetchedAt: lastMsg.created_at
            }));
            setLastFetchedAt(lastMsg.created_at);
         }
        return newMsgs;
      });
      
    } catch (error) {
      console.error('Send error:', error);
      // Update status to error
      setMessages(prev => prev.map(m => 
        m.local_id === tempId ? { ...m, status: 'error' } : m
      ));
      
      if (!attachment && !extra) {
        // Add to offline queue
        const queueKey = ticketId ? `offline_queue_ticket_${ticketId}` : `offline_queue_user_${userId}`;
        const queue: OfflineMessage[] = JSON.parse(localStorage.getItem(queueKey) || '[]');
        queue.push({ content, tempId, timestamp: Date.now() });
        localStorage.setItem(queueKey, JSON.stringify(queue));
        
        message.error('发送失败，已保存到离线队列，网络恢复后将自动重试');
      } else {
        message.error('发送失败');
      }
    }
  };

  // Retry offline messages
  const retryOfflineMessages = async () => {
    if (!userId) return;
    const queueKey = ticketId ? `offline_queue_ticket_${ticketId}` : `offline_queue_user_${userId}`;
    const queue: OfflineMessage[] = JSON.parse(localStorage.getItem(queueKey) || '[]');
    if (queue.length === 0) return;

    message.loading('正在发送离线消息...', 1);
    
    const newQueue: OfflineMessage[] = [];
    let successCount = 0;

    for (const item of queue) {
      try {
        const res: any = await sendChatMessage(userId, item.content, undefined, undefined, { ticket_id: ticketId || undefined });
        // Update the specific message in the list from error/sending to sent
        setMessages(prev => prev.map(m => 
            (m.local_id === item.tempId || (m.content === item.content && m.status === 'error')) 
            ? { ...res, status: 'sent' } 
            : m
        ));
        successCount++;
      } catch (e) {
        newQueue.push(item);
      }
    }
    
    localStorage.setItem(queueKey, JSON.stringify(newQueue));
    
    if (successCount > 0) {
      message.success(`${successCount} 条离线消息已发送`);
      // Force a poll to sync everything
      fetchMessages(userId, lastFetchedAt);
    }
  };

  // Check for online status to retry
  useEffect(() => {
    const handleOnline = () => retryOfflineMessages();
    window.addEventListener('online', handleOnline);
    
    // Also retry on mount if online
    if (navigator.onLine) {
        retryOfflineMessages();
    }

    return () => window.removeEventListener('online', handleOnline);
  }, [userId]);

  return { messages, loading, sendMessage };
}
