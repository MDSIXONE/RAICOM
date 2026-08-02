# WiFi热点配置管理器 - Python版本

这是原C#版本的Python实现，提供相同的功能：

## 功能特性

1. **WiFi热点管理**
   - 自动创建和管理WiFi热点
   - 支持WPA2安全认证
   - 可配置SSID、密码、频道等参数

2. **Web配置界面**
   - 简洁的HTML界面
   - 支持WiFi网络扫描
   - 实时状态反馈
   - 二维码生成

3. **网络连接管理**
   - 自动检测网络状态
   - 智能切换热点/WiFi模式
   - 连接失败自动回退

4. **设备兼容性改进**
   - 使用频道6提高手机兼容性
   - 改进的网络接口管理
   - 更好的错误处理和重试机制

## 安装要求

### 系统要求
- Linux系统（推荐Raspberry Pi OS）
- Python 3.7+
- NetworkManager
- 无线网卡支持AP模式

### Python依赖
```bash
pip3 install -r requirements.txt
```

### 系统依赖
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install network-manager python3-pip

# 确保NetworkManager正在运行
sudo systemctl enable NetworkManager
sudo systemctl start NetworkManager
```

## 使用方法

### 1. 基本运行
```bash
# 需要root权限
sudo python3 wifi_hotspot_manager.py
```

### 2. 配置文件
编辑 `config.json` 来自定义设置：

```json
{
  "hotspot": {
    "ssid": "RaspberryPi5-Setup",
    "password": "12345678",
    "interface": "wlan0",
    "channel": 6,
    "ip": "10.42.0.1",
    "dhcp_start": "10.42.0.10",
    "dhcp_end": "10.42.0.50"
  },
  "web_server": {
    "port": 5241,
    "host": "0.0.0.0"
  },
  "country": "CN"
}
```

### 3. 访问配置界面

#### 热点模式
1. 连接到WiFi热点：`RaspberryPi5-Setup`
2. 打开浏览器访问：`http://10.42.0.1:5241`
3. 或扫描页面上的二维码

#### WiFi连接模式
如果设备已连接到WiFi，程序会显示实际的IP地址

## 工作流程

1. **启动检测**
   - 检查是否已连接WiFi网络
   - 如果已连接，启动Web服务器
   - 如果未连接，创建热点

2. **热点模式**
   - 创建WiFi热点
   - 启动Web配置服务器
   - 生成配置二维码

3. **WiFi配置**
   - 用户通过Web界面输入WiFi信息
   - 程序尝试连接指定WiFi
   - 连接成功后切换到WiFi模式
   - 连接失败则回退到热点模式

## 故障排除

### 常见问题

1. **权限错误**
   ```
   错误: 此程序需要root权限运行
   ```
   解决：使用 `sudo` 运行程序

2. **NetworkManager未运行**
   ```bash
   sudo systemctl start NetworkManager
   ```

3. **无线接口不可用**
   - 检查无线网卡是否支持AP模式
   - 确认接口名称（通常是wlan0）
   ```bash
   nmcli device status
   ```

4. **端口被占用**
   - 修改config.json中的端口号
   - 或停止占用端口的程序

### 调试模式
程序会输出详细的日志信息，包括：
- 命令执行过程
- 网络状态变化
- 错误信息和堆栈跟踪

## 与C#版本的差异

### 改进之处
1. **更好的错误处理**：Python版本有更详细的错误信息和恢复机制
2. **简化的依赖**：不需要.NET运行时，只需Python和几个包
3. **更灵活的配置**：JSON配置文件更容易编辑
4. **跨平台兼容性**：可以在更多Linux发行版上运行

### 功能对等
- ✅ WiFi热点创建和管理
- ✅ Web配置界面
- ✅ 二维码生成
- ✅ 网络扫描
- ✅ 自动模式切换
- ✅ 频道6兼容性改进

## 开发说明

### 代码结构
- `wifi_hotspot_manager.py`：主程序文件
- `config.json`：配置文件
- `requirements.txt`：Python依赖
- `README.md`：使用说明

### 扩展功能
可以通过修改代码添加：
- 多语言支持
- 更多网络配置选项
- 状态监控API
- 日志文件输出

## 许可证

与原项目保持相同的许可证。