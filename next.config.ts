import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["echarts", "zrender"],
  // 局域网（VMnet8/内网）访问 dev 资源必须显式放行，否则图片/_next 资源被拦截
  allowedDevOrigins: ["26.104.66.42"],
  // 项目位于嵌套目录（上层另一 git 仓库），显式指定 root 消除 package-lock 忽略警告
  turbopack: { root: process.cwd() },
};

export default nextConfig;
