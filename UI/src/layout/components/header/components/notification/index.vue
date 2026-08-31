<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { Bell } from "@element-plus/icons-vue";
import { Tooltip } from "@/components";
import { useNamespace } from "@/composables";
import { useMessageStore } from "@/pinia";
import { t } from "@/common/languages";
import message1 from "@/common/assets/images/message/msg01.png";
import message2 from "@/common/assets/images/message/msg02.png";
import message3 from "@/common/assets/images/message/msg03.png";
import message4 from "@/common/assets/images/message/msg04.png";
import message5 from "@/common/assets/images/message/msg05.png";
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

onMounted(() => {
  // 请求获取消息列表
  messageStore.getMessageList();
});

/**
 * 通知列表
 */
const noticeList: Notice[] = [
  { id: "1", avatar: message1, title: t("_headerBar.noticeWeeklyReport"), date: t("_headerBar.timeOneMinuteAgo") },
  { id: "2", avatar: message2, title: t("_headerBar.noticeFourMeetings"), date: t("_headerBar.timeOneHourAgo") },
  { id: "3", avatar: message3, title: t("_headerBar.noticeFrontendInterview"), date: t("_headerBar.timeOneDayAgo") },
  {
    id: "4",
    avatar: message4,
    title: t("_headerBar.noticeConsumptionDrill"),
    date: t("_headerBar.timeOneWeekAgo"),
  },
  { id: "5", avatar: message5, title: t("_headerBar.noticeTalentAward"), date: "2023-01-01" },
];

/**
 * 代办列表
 */
const arList: Notice[] = [
  {
    id: "1",
    title: t("_headerBar.todoTeekDesign"),
    description: t("_headerBar.todoTeekDesign"),
    tag: [
      { name: t("_headerBar.priorityHigh"), type: "danger" },
      { name: t("_headerBar.tagExpired", { n: 7 }), type: "danger" },
    ],
    date: "2099-12-31",
  },
  {
    id: "2",
    title: t("_headerBar.todoItReviewMeeting"),
    description: t("_headerBar.todoItMeetingDesc"),
    tag: [
      { name: t("_headerBar.priorityMedium"), type: "warning" },
      { name: t("_headerBar.tagInProgress"), type: "primary" },
    ],
    date: "2023-09-15",
  },
  {
    id: "3",
    title: t("_headerBar.notice"),
    description: t("_headerBar.todoApiGateway"),
    tag: [
      { name: t("_headerBar.priorityLow"), type: "info" },
      { name: t("_headerBar.tagDaysUntilOverdue", { n: 2 }), type: "warning" },
    ],
    date: "2023-12-31",
  },
  {
    id: "4",
    title: t("_headerBar.todoDevelopEts"),
    description: t("_headerBar.todoEtsDesc"),
    tag: [{ name: t("_headerBar.priorityHigh"), type: "danger" }],
    date: "2023-07-27",
  },
];

const activeName = ref("notice");

// 标签列表
const tabList = computed<TabInfo[]>(() => [
  { name: "notice", label: t("_headerBar.notice"), data: noticeList },
  {
    name: "message",
    label: t("_headerBar.message"),
    data: unreadMessageList.value.map((item: Notice) => {
      item.avatar = message2;
      return item;
    }),
  },
  { name: "ar", label: t("_headerBar.todo"), data: arList },
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
