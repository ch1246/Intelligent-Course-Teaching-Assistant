<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { Bell } from "@element-plus/icons-vue";
import { Tooltip } from "@/components";
import { useNamespace } from "@/composables";
import { useMessageStore } from "@/pinia";
import { t } from "@/common/languages";
import message2 from "@/common/assets/images/message/msg02.png";
import "./index.scss";

defineOptions({ name: "Notification" });

interface Notice {
  /** 消息 id */
  id: string;
  /** 消息头像 */
  avatar?: string;
  /** 消息标题 */
  title: string;
  /** 消息描述 */
  description?: string;
  /** 消息日期 */
  date?: string;
  /** 消息创建时间 */
  createTime?: string;
  /** 消息标签 */
  tag?: {
    name: string;
    type: "primary" | "danger" | "success" | "info" | "warning";
  }[];
}

interface TabInfo {
  /** 标签名称 */
  name: string;
  /** 标签名称 */
  label: string;
  /** 标签数据 */
  data: Notice[];
}

const messageStore = useMessageStore();
const { unreadMessageList } = storeToRefs(messageStore);

const ns = useNamespace("notification");
const router = useRouter();

onMounted(async () => {
  // 请求获取消息列表
  await messageStore.getMessageList();
  // 将未读消息同步到通知列表
  noticeList.value = unreadMessageList.value.map((item, idx) => ({
    id: item.id || String(idx),
    title: item.title,
    description: item.description,
    date: item.createTime,
  }));
});

/**
 * 通知列表 — 从消息 API 获取真实数据
 */
const noticeList = ref<Notice[]>([]);

/**
 * 待办列表 — 暂无后端 API，显示空状态
 */
const arList = ref<Notice[]>([]);

const activeName = ref("notice");

// 标签列表
const tabList = computed<TabInfo[]>(() => [
  { name: "notice", label: t("_headerBar.notice"), data: noticeList.value },
  {
    name: "message",
    label: t("_headerBar.message"),
    data: unreadMessageList.value.map((item: Notice) => {
      item.avatar = message2;
      return item;
    }),
  },
  { name: "ar", label: t("_headerBar.todo"), data: arList.value },
]);

/**
 * 跳转消息中心
 */
const toDetail = () => {
  if (activeName.value === "message") router.push("/message");
};
</script>

<template>
  <div :class="ns.b()">
    <el-popover placement="bottom" :width="360" trigger="click" :popper-class="ns.b()">
      <template #reference>
        <div class="flx-center" style="width: 100%; height: 100%; margin-top: 5px">
          <el-badge is-dot>
            <Icon :icon="Bell" />
          </el-badge>
        </div>
      </template>

      <el-tabs v-model="activeName">
        <el-tab-pane
          v-for="item in tabList"
          :key="item.name"
          :label="`${item.label} (${item.data.length})`"
          :name="item.name"
        >
          <template v-if="item.data.length > 0">
            <el-scrollbar :max-height="400">
              <ul :class="ns.e('list')">
                <li v-for="data in item.data" :key="data.id" class="flx-align-center">
                  <img v-if="data.avatar" :src="data.avatar" alt="" :class="ns.m('avatar')" />

                  <div :class="ns.e('info')" class="flx-1">
                    <div class="flx-align-center-between">
                      <Tooltip :line="1">
                        <span class="title">{{ data.title }}</span>
                      </Tooltip>
                      <div v-if="data.tag?.length" class="flx" style="gap: 2px">
                        <ElTag v-for="tag in data.tag" :key="tag.name" :type="tag.type" size="small">
                          {{ tag.name }}
                        </ElTag>
                      </div>
                    </div>

                    <Tooltip v-if="data.description" :line="2">
                      <span class="desc">{{ data.description }}</span>
                    </Tooltip>

                    <span class="date">{{ data.date || data.createTime }}</span>
                  </div>
                </li>
              </ul>
            </el-scrollbar>

            <el-button @click="toDetail" style="width: 100%">{{ $t("_home.viewAll") }}</el-button>
          </template>

          <div :class="ns.e('empty')" v-else>
            <img src="@/common/assets/images/notData.png" alt="notData" />
            <div>{{ $t("_common.noContent") }}</div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-popover>
  </div>
</template>
