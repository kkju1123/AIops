// @vitest-environment jsdom

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PublicLandingView from "../src/views/PublicLandingView.vue";

const global = {
  stubs: {
    RouterLink: {
      props: ["to"],
      template: '<a :href="to"><slot /></a>'
    }
  }
};

describe("public portfolio experience", () => {
  it("explains the project and offers a frictionless preview before login", () => {
    const wrapper = mount(PublicLandingView, { global });

    expect(wrapper.get("h1").text()).toContain("真实证据");
    expect(wrapper.text()).toContain("Agent 对话");
    expect(wrapper.text()).toContain("知识检索");
    expect(wrapper.text()).toContain("智能诊断");
    expect(wrapper.text()).toContain("MCP 连接");
    expect(wrapper.get('.portfolio-view__primary').attributes("href")).toBe("/drill");
    expect(wrapper.get('.portfolio-view__primary').text()).toContain("进入工作台");
    expect(wrapper.find('a[href="/demo"]').exists()).toBe(false);
    expect(wrapper.get('a[href="/login"]').text()).toContain("登录");
    expect(wrapper.text()).toContain("临时访客账号");
    expect(wrapper.text()).toContain("故障模拟器生成");
  });
});
