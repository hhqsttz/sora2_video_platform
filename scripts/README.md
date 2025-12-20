# 实用脚本

此文件夹包含用于轻松管理 Sora2 视频平台的脚本。

- **`start_server.bat`**: 一键启动后端服务器并打开 Web 界面。
- **`run_tests.bat`**: 运行自动化测试套件 (`test_api.py`) 以验证所有功能。
- **`install_dependencies.bat`**: 安装所需的 Python 依赖包。
- **`build_exe.bat`**: 将应用程序打包为独立的 `.exe` 文件（位于 `build_artifacts/dist` 中）。

**注意：** 这些脚本配置为自动优先使用 `E:\my_env\fastapi_env` 环境（如果存在），否则回退到系统默认的 `python`。
