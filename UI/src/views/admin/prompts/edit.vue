<template>
  <div class="prompt-edit-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-button @click="$router.back()" text>{{ $t("_prompts.back") }}</el-button>
          <span>{{ isEdit ? $t("_prompts.editTitle") : $t("_prompts.createTitle") }}</span>
        </div>
      </template>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px" style="max-width: 900px">
        <el-form-item :label="$t('_prompts.name')" prop="name">
          <el-input v-model="form.name" :placeholder="$t('_prompts.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('_prompts.skill')" prop="skill">
          <el-select v-model="form.skill" style="width: 200px">
            <el-option :label="$t('_prompts.skillQA')" value="qa" />
            <el-option :label="$t('_prompts.skillFormula')" value="formula" />
            <el-option :label="$t('_prompts.skillCode')" value="code_debug" />
            <el-option :label="$t('_prompts.skillLab')" value="lab_guide" />
            <el-option :label="$t('_prompts.skillPaper')" value="paper_reader" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('_prompts.description')">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            :placeholder="$t('_prompts.descriptionPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('_prompts.content')" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="18"
            :placeholder="$t('_prompts.contentPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('_prompts.changeNote')" v-if="isEdit">
          <el-input v-model="form.change_note" :placeholder="$t('_prompts.changeNotePlaceholder')" />
        </el-form-item>
        <el-form-item v-if="isEdit" :label="$t('_prompts.preview')">
          <el-row :gutter="12" style="width: 100%">
            <el-col :span="12">
              <el-input
                v-model="previewVars.course_name"
                placeholder="course_name"
                size="small"
                style="margin-bottom: 6px"
              />
              <el-input
                v-model="previewVars.retrieval_docs"
                placeholder="retrieval_docs"
                size="small"
                style="margin-bottom: 6px"
              />
              <el-input
                v-model="previewVars.memory_prompt"
                placeholder="memory_prompt"
                size="small"
                style="margin-bottom: 6px"
              />
              <el-input
                v-model="previewVars.user_question"
                placeholder="user_question"
                size="small"
                style="margin-bottom: 6px"
              />
            </el-col>
            <el-col :span="12" style="display: flex; flex-direction: column; gap: 6px">
              <el-button size="small" type="primary" @click="handlePreview" :loading="previewLoading">
                {{ $t("_prompts.previewBtn") }}
              </el-button>
              <el-input
                v-model="previewResult"
                type="textarea"
                :rows="8"
                readonly
                :placeholder="$t('_prompts.previewResult')"
              />
            </el-col>
          </el-row>
        </el-form-item>
        <el-form-item>
          <el-switch v-model="form.is_active" :active-text="$t('_prompts.enable')" />
          <el-switch v-model="form.is_default" :active-text="$t('_prompts.setDefault')" style="margin-left: 20px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">{{ $t("_prompts.save") }}</el-button>
          <el-button @click="$router.back()">{{ $t("_prompts.cancel") }}</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { FormInstance } from "element-plus";
import { ElMessage } from "element-plus";
import { http } from "@/common/http";
import { t } from "@/common/languages";

defineOptions({ name: "AdminPromptsEdit" });

const route = useRoute();
const router = useRouter();
const isEdit = computed(() => !!route.params.id);

const formRef = ref<FormInstance>();
const submitting = ref(false);
const previewLoading = ref(false);
const previewResult = ref("");

const form = reactive<any>({
  name: "",
  skill: "qa",
  description: "",
  content: "",
  is_active: true,
  is_default: false,
  change_note: "",
});

const rules = {
  name: [{ required: true, message: t("_prompts.nameRequired") }],
  content: [{ required: true, message: t("_prompts.contentRequired") }],
};

const previewVars = reactive({
  course_name: t("_prompts.previewCourseName"),
  retrieval_docs: t("_prompts.previewRetrievalDocs"),
  memory_prompt: "",
  user_question: t("_prompts.previewUserQuestion"),
});

onMounted(async () => {
  if (isEdit.value) {
    try {
      const res: any = await http.get(`/admin/prompts/${route.params.id}`);
      Object.assign(form, res.data);
    } catch (err: any) {
      ElMessage.error(err?.message || t("_prompts.loadFailed"));
      router.back();
    }
  }
});

async function handlePreview() {
  previewLoading.value = true;
  const id = route.params.id;
  if (!id) {
    previewLoading.value = false;
    return;
  }
  try {
    const res: any = await http.post(`/admin/prompts/${id}/preview`, { variables: previewVars });
    previewResult.value = res.data?.rendered || res.data || JSON.stringify(res);
  } catch {
    previewResult.value = t("_prompts.renderFailed");
  } finally {
    previewLoading.value = false;
  }
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  submitting.value = true;
  const data = { ...form };
  try {
    if (isEdit.value) {
      await http.put(`/admin/prompts/${route.params.id}`, data);
    } else {
      await http.post("/admin/prompts", data);
    }
    ElMessage.success(isEdit.value ? t("_prompts.saveSuccess") : t("_prompts.createSuccess"));
    router.back();
  } catch (err: any) {
    ElMessage.error(err?.message || t("_prompts.saveFailed"));
  } finally {
    submitting.value = false;
  }
}
</script>
