import { ref } from "vue";
import { defineStore } from "pinia";
import { http } from "@/common/http";

export interface Course {
  id: number;
  name: string;
  description: string;
  coverColor: string;
  chapters: number;
  progress: number;
  lastStudyTime: string;
  icon: any;
}

export const useCourseStore = defineStore("courseStore", () => {
  const courses = ref<Course[]>([]);

  const loadMyCourses = async () => {
    try {
      const res = await http.get<httpNs.Response<any[]>>("/course/my-courses");
      courses.value = (res.data || []).map((c: any) => ({
        id: c.id,
        name: c.name,
        description: c.description || "",
        coverColor: c.cover_color || "var(--tk-bg-primary)",
        chapters: c.chapters || 0,
        progress: 0,
        lastStudyTime: "",
        icon: null,
      }));
    } catch {
      courses.value = [];
    }
  };

  return { courses, loadMyCourses };
});
