import { ref } from "vue";
import { defineStore } from "pinia";
import { http } from "@/common/http";

export interface MessageItem {
  id: string;
  title: string;
  content: string;
  description?: string;
  createTime: string;
  loading?: boolean;
}

export const useMessageStore = defineStore("messageStore", () => {
  const unreadMessageList = ref<MessageItem[]>([]);
  const hasReadMessageList = ref<MessageItem[]>([]);
  const recycleMessageList = ref<MessageItem[]>([]);

  const getMessageList = async () => {
    try {
      const res = await http.get<httpNs.Response<any>>("/messages");
      const data = res.data || {};
      unreadMessageList.value = (data.unread || []).map(toMsg);
      hasReadMessageList.value = (data.read || []).map(toMsg);
      recycleMessageList.value = (data.recycle || []).map(toMsg);
    } catch {
      // fallback to empty
    }
  };

  const toMsg = (m: any): MessageItem => ({
    id: m.id || "",
    title: m.title || "",
    content: m.content || "",
    description: m.description || "",
    createTime: m.createTime || "",
    loading: false,
  });

  const messageHasRead = ({ id }: { id: string }) => {
    moveMessage({ to: "hasReadMessageList", from: "unreadMessageList", id });
    return Promise.resolve("");
  };

  const removeReadMessage = ({ id }: { id: string }) => {
    moveMessage({ to: "recycleMessageList", from: "hasReadMessageList", id });
    return Promise.resolve("");
  };

  const restoreRecycleMessage = ({ id }: { id: string }) => {
    moveMessage({ to: "hasReadMessageList", from: "recycleMessageList", id });
    return Promise.resolve("");
  };

  const moveMessage = (route: {
    to: "hasReadMessageList" | "recycleMessageList";
    from: "unreadMessageList" | "hasReadMessageList" | "recycleMessageList";
    id: string;
  }) => {
    const store = useMessageStore();
    const { from, to, id } = route;
    const idx = store[from].findIndex((item: MessageItem) => item.id === id);
    if (idx < 0) return;
    const item = store[from].splice(idx, 1)[0];
    item.loading = false;
    store[to].unshift(item);
  };

  return {
    unreadMessageList,
    hasReadMessageList,
    recycleMessageList,
    getMessageList,
    messageHasRead,
    removeReadMessage,
    restoreRecycleMessage,
  };
});
