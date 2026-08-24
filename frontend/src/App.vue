<template>
  <el-container class="layout">
    <el-header class="header">
      <div class="logo">景文智核</div>
      <el-menu mode="horizontal" :default-active="$route.path" router class="menu">
        <el-menu-item index="/chat">智能问答</el-menu-item>
        <el-menu-item index="/attractions">景点检索</el-menu-item>
        <el-menu-item index="/routes">线路检索</el-menu-item>
        <el-menu-item index="/info">实用信息</el-menu-item>
        <el-menu-item index="/admin/import">内容导入</el-menu-item>
        <el-menu-item index="/admin/documents">元数据管理</el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="main">
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </el-main>
  </el-container>
</template>

<style>
* {
  box-sizing: border-box;
}
body {
  margin: 0;
}
.layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.header {
  height: 60px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 20px;
}
.logo {
  font-weight: 700;
  font-size: 18px;
  margin-right: 40px;
  color: #409eff;
}
.menu {
  flex: 1;
  border-bottom: none;
}
.main {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 16px;
}
.main > * {
  height: 100%;
  overflow: auto;
}
</style>
