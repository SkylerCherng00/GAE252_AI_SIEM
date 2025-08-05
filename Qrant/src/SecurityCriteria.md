# MITRE ATT&CK® Enterprise — Web Server Attack Techniques Knowledge Base
**Last Updated**: 2025-08-02 UTC+8  
**Source**: [MITRE ATT&CK® for Enterprise Matrix](https://attack.mitre.org/matrices/enterprise/)

> This document strictly follows the MITRE ATT&CK® for Enterprise framework to select and detail attack tactics and techniques that are directly related to web-server security. Each technique node includes the official description, key log indicators, corresponding mitigation IDs, and concrete attack-flow examples, all designed to enhance RAG knowledge in security-automation systems (e.g., SIEM/SOAR).

---

## **TA0001: Initial Access**

### **T1190: Exploit Public-Facing Application**
-  **Description**: Attackers exploit software vulnerabilities in public-facing web servers, CMSs (e.g., WordPress), application frameworks (e.g., Apache Struts), or libraries (e.g., Log4j) to gain an initial foothold in the network.  
-  **Key Indicators**:  
    - **Web-server logs (`access.log`, `error.log`)**:  
        - Unexpected, specially encoded strings appear in the URI, such as the Log4Shell pattern `${jndi:ldap://...}`.  
        - The User-Agent field contains known scanner names such as `nmap`, `wpscan`, `feroxbuster`, or `Metasploit`.  
        - A burst of 404 Not Found responses for different paths is quickly followed by a 200 OK or 500 Internal Server Error, often indicating vulnerability probing.  
    - **Process monitoring**: Web-server worker processes (`httpd`, `nginx`) spawn unexpected child processes such as `sh`, `bash`, or `powershell.exe`.  
-  **Mitigations**:  
    - `M1051`: Patch software promptly to fix known vulnerabilities.  
    - `M1046`: Perform regular vulnerability scans to identify and remediate weaknesses in public-facing applications.  
    - `M1011`: Deploy a network-based intrusion-prevention system (NIPS) or web application firewall (WAF) to detect and block known exploit attempts.  
-  **Example Attack Flow**:  
    1. The attacker sends a `GET` request containing a malicious JNDI string in the User-Agent header.  
    2. A vulnerable Java application on the server logs this User-Agent value.  
    3. Log4j parses the malicious string and requests an attacker-controlled LDAP server.  
    4. The application downloads and executes a serialized Java payload from the malicious LDAP server.  
    5. A reverse shell is launched, giving the attacker control of the `www-data` account on the web server.  

### **T1110: Brute Force**
-  **Description**: Attackers systematically try large numbers of credential combinations to obtain account access. Common sub-techniques include `T1110.001 Password Guessing` and `T1110.003 Password Spraying`.  
-  **Key Indicators**:  
    - **Web-server log (`access.log`)**: Numerous `POST` requests from a single IP to login pages (e.g., `/wp-login.php`, `/admin/login`) accompanied by consecutive HTTP 401/403 responses or 200 responses containing login-failure messages.  
    - **System authentication logs (`/var/log/auth.log`, `secure`)**: Large numbers of `Failed password for <user> from <IP>` entries for services such as SSH or FTP.  
-  **Mitigations**:  
    - `M1029`: Enforce multi-factor authentication (MFA).  
    - `M1038`: Limit failed login attempts and temporarily lock accounts after a threshold is reached.  
    - `M1033`: Rate-limit requests originating from a single source.  

---

## **TA0002: Execution**

### **T1059: Command and Scripting Interpreter**
-  **Description**: After exploitation, attackers use built-in interpreters (e.g., `bash`, `Python`, `PHP`) on the target system to run arbitrary commands.  
-  **Key Indicators**:  
    - **Process monitoring (`auditd`, `Sysmon`)**: Web-server processes (`php-fpm`, `nginx`) create atypical child processes such as `/bin/sh`, `curl`, or `wget`.  
    - **Web-server log (`access.log`)**: Requests to a web shell file (e.g., `shell.php`) whose query string contains system commands such as `?cmd=ls+-la`.  
-  **Mitigations**:  
    - `M1045`: Apply application-control policies that restrict which commands and scripts the web-server process may run.  
    - `M1026`: Disable or restrict unnecessary interpreters.  

---

## **TA0003: Persistence**

### **T1505.003: Server Software Component — Web Shell**
-  **Description**: Attackers place a malicious script (web shell) in a web-accessible directory to gain persistent remote access to the server.  
-  **Key Indicators**:  
    - **File-integrity monitoring (FIM)**: Newly created `.php`, `.jsp`, `.aspx`, or similar scripts are detected in the web root, upload, or temporary directories.  
    - **Web-server log (`access.log`)**:  
        - An uncommon script repeatedly receives `POST` requests from a single IP.  
        - The User-Agent in these requests is often `curl`, `python-requests`, or another non-standard browser string.  
-  **Mitigations**:  
    - `M1050`: Regularly scan web content for known web-shell signatures.  
    - `M1022`: Restrict file and directory permissions so the web-service account cannot create or modify executables outside required paths.  
    - Configure the web server to disallow script execution in upload directories.  

---

## **TA0005: Defense Evasion**

### **T1027: Obfuscated Files or Information**
-  **Description**: Attackers obfuscate malicious files (e.g., web shells) or commands to evade signature-based detection. Common methods include Base64 encoding, Gzip compression, and string reversal.  
-  **Key Indicators**:  
    - **Static-file analysis**: PHP or other script files contain large Base64-encoded blocks along with decoding functions such as `eval()`, `gzuncompress()`, or `base64_decode()`.  
-  **Mitigations**:  
    - `M1048`: Apply behavioral analysis to network traffic and endpoint files rather than relying solely on signatures.  
    - `M1021`: Restrict or monitor the use of interpreters and tools commonly used for obfuscation.  

---

## **TA0006: Credential Access**

### **T1552.001: Credentials in Files**
-  **Description**: Attackers search the compromised server for files that contain plaintext or weakly encrypted credentials.  
-  **Key Indicators**:  
    - **File-access auditing (`auditd`)**: The web-service process (`www-data`) reads unexpected sensitive configuration files such as `wp-config.php`, `.env`, `/etc/shadow`, or `~/.aws/credentials`.  
    - **Shell history (`.bash_history`)**: Contains `cat`, `grep`, `find`, or similar commands targeting known credential files.  
-  **Mitigations**:  
    - `M1022`: Apply strict access controls to credential files.  
    - `M1028`: Store sensitive credentials in a secure vault instead of plaintext configuration files.  

---

## **TA0040: Impact**

### **T1491.001: Defacement**
-  **Description**: Attackers modify a website’s appearance, replacing it with their own content to damage reputation, spread propaganda, or protest.  
-  **Key Indicators**:  
    - **File-integrity monitoring (FIM)**: Core site files such as `index.html` or `index.php` are modified.  
    - **Web-server log (`access.log`)**: `POST` or `PUT` requests to core files immediately before the defacement.  
-  **Mitigations**:  
    - `M1053`: Maintain backups of critical content for rapid restoration after defacement.  
    - `M1022`: Enforce strict write permissions on the web root and core files.  

---

## **TA0007: Discovery**

### **T1082: System Information Discovery**
-  **Description**: Attackers gather host details—OS version, hardware specs, hostname—to prepare for privilege escalation or lateral movement.  
-  **Key Indicators**:  
    - **Process monitoring (`auditd`, `Sysmon`)**: The web-service account (`www-data`) runs information-gathering commands such as `uname -a`, `lscpu`, `hostname`, or `systeminfo`.  
    - **Web-shell activity**: Command logs show the above system commands executed via the web shell.  
-  **Mitigations**:  
    - `M1047`: Use application whitelisting or execution-prevention policies to limit the web-service account from running unnecessary system binaries.  
    - `M1036`: Monitor process-creation events, especially child processes of web-server processes, and alert on suspicious behavior such as running `uname`.  

### **T1046: Network Service Discovery**
-  **Description**: Attackers probe the internal network to identify live hosts and services for potential lateral movement.  
-  **Key Indicators**:  
    - **Process monitoring**: The web-service process runs scanning tools such as `nmap`, `netstat -an`, `ss -tulpn`, or manually runs `curl` or `telnet` to connect to internal IPs and ports.  
    - **Network-traffic monitoring**: The web server initiates numerous TCP/UDP connections to internal hosts, especially common service ports (22, 3306, 3389, 8080).  
-  **Mitigations**:  
    - `M1018`: Use a host-based firewall to restrict outbound connections from the web server, allowing only required traffic.  
    - `M1036`: Monitor outbound connections and alert when the web server contacts many internal IPs or ports.  

### **T1057: Process Discovery**
-  **Description**: Attackers list running processes to learn about current activity, running services (e.g., databases, security software), and potential targets.  
-  **Key Indicators**:  
    - **Process monitoring**: The web-service process executes `ps aux`, `tasklist`, `top`, etc.  
    - **Command-line logs**: Shell or web-shell histories contain process-listing commands.  
-  **Mitigations**:  
    - `M1036`: Monitor process creation and command-line arguments, alerting on the web-server process running `ps` or `tasklist`.  

---

## **TA0008: Lateral Movement**

### **T1021.001: Remote Desktop Protocol**
-  **Description**: After gaining a foothold (e.g., on a web server) and valid credentials, attackers may use RDP to connect to other internal Windows hosts.  
-  **Key Indicators**:  
    - **Network-traffic monitoring**: Outbound TCP connections from the web server to internal hosts on port 3389.  
    - **Windows security logs (target host)**: Event IDs `4624` (successful login) or `4625` (failed login) with the source IP set to the web server.  
-  **Mitigations**:  
    - `M1018`: Configure a host firewall on the web server to block unnecessary outbound RDP.  
    - `M1029`: Enforce Network Level Authentication (NLA) and MFA on internal servers.  

### **T1021.002: SMB/Windows Admin Shares**
-  **Description**: Attackers leverage SMB to access remote admin shares (e.g., `C$`, `ADMIN$`) for file transfer or remote execution.  
-  **Key Indicators**:  
    - **Network-traffic monitoring**: Outbound TCP connections from the web server to internal hosts on port 445.  
    - **Windows security logs (target host)**: Event IDs `5140` (share accessed) or `5145` (detailed share access) originating from the web-server IP.  
-  **Mitigations**:  
    - `M1018`: Restrict outbound SMB traffic from the web server.  
    - `M1043`: Disable unnecessary admin shares for inter-server communication.  

---

## **TA0009: Collection**

### **T1005: Data from Local System**
-  **Description**: Attackers collect files of interest from the local file system for later exfiltration.  
-  **Key Indicators**:  
    - **File-access auditing (`auditd`)**: The web-service account reads large numbers of files or accesses directories outside its normal scope, such as `/home` or `/var/lib/mysql`.  
    - **Process monitoring**: The `www-data` user runs compression utilities (`tar`, `zip`, `gzip`) to package multiple files or directories.  
-  **Mitigations**:  
    - `M1022`: Apply least-privilege principles so the web-service account can read only the minimum set of files required.  
    - `M1059`: Monitor sensitive directories for abnormal mass-read behavior and alert.  

### **T1114.001: Local Email Collection**
-  **Description**: If the web server also hosts or stores email data (e.g., `.pst`, `.mbox`), attackers may collect these files to obtain sensitive information.  
-  **Key Indicators**:  
    - **File-access auditing**: The web-service account reads mail-storage files under `/var/mail/` or user home directories.  
-  **Mitigations**:  
    - `M1001`: Avoid storing sensitive email data on public-facing web servers.  
    - `M1022`: Strictly limit access to mail-storage directories.  

---

## **TA0010: Exfiltration**

### **T1041: Exfiltration Over C2 Channel**
-  **Description**: Attackers use an established command-and-control (C2) channel—such as HTTP/HTTPS traffic from a web shell—to transmit stolen data, blending it with normal web traffic.  
-  **Key Indicators**:  
    - **Network-traffic monitoring**:  
        - HTTP `POST` requests from the web server to external IPs with abnormally large response bodies (e.g., multi-MB archives).  
        - DNS logs show the web server resolving uncommon or randomly generated domains, possibly for DNS-tunneling exfiltration.  
-  **Mitigations**:  
    - `M1037`: Baseline outbound web traffic and alert on anomalies in size or frequency.  
    - `M1020`: Use DNS whitelisting or sinkhole techniques to prevent resolution of malicious or unauthorized domains.  

---

# MITRE ATT&CK® Enterprise — Web 伺服器攻擊技術知識庫
**最後更新**: 2025-08-02 UTC+8
**資料來源**: [MITRE ATT&CK® for Enterprise Matrix](https://attack.mitre.org/matrices/enterprise/)

> 本文件嚴格依據 MITRE ATT&CK® for Enterprise 框架，篩選並詳述與 Web 伺服器安全直接相關的攻擊戰術（Tactic）與技術（Technique）。每個技術節點均包含官方描述、關鍵日誌徵象、對應的緩解措施 ID 以及具體的攻擊案例流程，專為資安自動化分析系統（如 SIEM/SOAR）的 RAG 知識增強而設計。

---

## **TA0001: Initial Access (初始訪問)**

### **T1190: Exploit Public-Facing Application (利用面向公眾的應用程式)**
-   **描述**: 攻擊者利用對外 Web 伺服器、CMS（如 WordPress）、應用框架（如 Apache Struts）或函式庫（如 Log4j）中存在的軟體漏洞來獲取初步的網路立足點。
-   **關鍵徵象**:
    -   **Web Server Log (`access.log`, `error.log`)**:
        -   URI 中出現非預期的、經特殊編碼的字串，例如針對 Log4Shell 的 `${jndi:ldap://...}`。
        -   User-Agent 欄位出現已知的掃描工具名稱，如 `nmap`, `wpscan`, `feroxbuster`, `Metasploit`。
        -   在短時間內出現大量針對不同路徑的 404 Not Found 回應，緊接著出現一個 200 OK 或 500 Internal Server Error，這通常是漏洞探測的跡象。
    -   **系統程序監控**: Web 伺服器（`httpd`, `nginx`）的工作程序（worker process）衍生出非預期的子程序，如 `sh`, `bash`, `powershell.exe`。
-   **防禦/緩解**:
    -   `M1051`: 及時更新軟體，修補已知的安全漏洞。
    -   `M1046`: 定期進行漏洞掃描，識別並修復面向公眾的應用程式中的弱點。
    -   `M1011`: 使用網路入侵防禦系統（NIPS）或 Web 應用程式防火牆（WAF）來偵測與阻擋已知的漏洞利用嘗試。
-   **案例流程**:
    1.  攻擊者向 Web 伺服器發送一個帶有惡意 JNDI 字串的 `GET` 請求，該字串位於 HTTP Header 的 User-Agent 中。
    2.  伺服器上運行的、存在 Log4Shell 漏洞的 Java 應用程式記錄了此 User-Agent。
    3.  Log4j 組件解析了惡意字串，觸發了對攻擊者控制的惡意 LDAP 伺服器的請求。
    4.  應用程式從惡意 LDAP 伺服器下載並執行了一個序列化的 Java Payload。
    5.  最終，一個反向 Shell（reverse shell）被執行，攻擊者成功獲取了 Web 伺服器 `www-data` 使用者的控制權。

### **T1110: Brute Force (暴力破解)**
-   **描述**: 攻擊者通過系統性地嘗試大量可能的憑證組合，來猜測並獲取帳號的存取權限。常見的子技術包括 `T1110.001: Password Guessing`（密碼猜測）和 `T1110.003: Password Spraying`（密碼噴灑）。
-   **關鍵徵象**:
    -   **Web Server Log (`access.log`)**: 來自單一 IP 地址，針對登入頁面（如 `/wp-login.php`, `/admin/login`）的大量 `POST` 請求，並伴隨著連續的 HTTP 401/403 回應或包含登入失敗訊息的 200 回應。
    -   **系統驗證日誌 (`/var/log/auth.log`, `secure`)**: 針對 SSH、FTP 等服務的大量 `Failed password for <user> from <IP>` 登入失敗紀錄。
-   **防禦/緩解**:
    -   `M1029`: 使用多因素驗證（MFA）來增加暴力破解的難度。
    -   `M1038`: 限制帳號的登入失敗次數，在達到閾值後暫時鎖定帳號。
    -   `M1033`: 限制來自單一來源的請求速率。

---

## **TA0002: Execution (執行)**

### **T1059: Command and Scripting Interpreter (命令與腳本直譯器)**
-   **描述**: 攻擊者利用目標系統上已有的腳本語言直譯器（如 `bash`, `Python`, `PHP`）來執行任意命令，通常作為漏洞利用成功後的下一步。
-   **關鍵徵象**:
    -   **程序監控 (`auditd`, `Sysmon`)**: Web 伺服器程序（`php-fpm`, `nginx`）創建了非典型的子程序，如 `/bin/sh`, `curl`, `wget`。
    -   **Web Server Log (`access.log`)**: 針對某個 Web Shell 檔案（如 `shell.php`）的請求中，其查詢參數包含系統命令，如 `?cmd=ls+-la`。
-   **防禦/緩解**:
    -   `M1045`: 實施應用程式控制策略，限制特定程序（如 Web 伺服器）可以執行的命令與腳本。
    -   `M1026`: 禁用或限制不必要的腳本直譯器。

---

## **TA0003: Persistence (持久化)**

### **T1505.003: Server Software Component: Web Shell (伺服器軟體元件：Web Shell)**
-   **描述**: 攻擊者在 Web 伺服器的可訪問目錄下放置一個惡意腳本（Web Shell），從而獲得對伺服器的持久化遠端存取能力。
-   **關鍵徵象**:
    -   **檔案完整性監控 (FIM)**: 在網站根目錄、上傳目錄或暫存目錄下，偵測到新創建的 `.php`, `.jsp`, `.aspx` 等腳本檔案。
    -   **Web Server Log (`access.log`)**:
        -   一個不常見的腳本檔案持續接收來自單一 IP 的 `POST` 請求。
        -   該檔案的存取日誌中，User-Agent 通常為 `curl`, `python-requests` 等非標準瀏覽器字串。
-   **防禦/緩解**:
    -   `M1050`: 利用漏洞掃描工具定期掃描 Web 內容，尋找已知的 Web Shell 簽章。
    -   `M1022`: 限制檔案與目錄的權限，禁止 Web 服務帳號在非必要目錄中創建或修改可執行檔案。
    -   在 Web 伺服器設定中，禁止上傳目錄執行腳本。

---

## **TA0005: Defense Evasion (防禦規避)**

### **T1027: Obfuscated Files or Information (混淆檔案或資訊)**
-   **描述**: 攻擊者對其惡意檔案（如 Web Shell）或命令進行混淆，以逃避基於簽章的檢測。常見方法包括 Base64 編碼、Gzip 壓縮、字串反轉等。
-   **關鍵徵象**:
    -   **靜態檔案分析**: PHP 或其他腳本檔案中包含大段的 Base64 編碼字串，並與 `eval()`, `gzuncompress()`, `base64_decode()` 等解碼函數一起出現。
-   **防禦/緩解**:
    -   `M1048`: 對網路流量與端點檔案進行行為分析，而非僅僅依賴簽章。
    -   `M1021`: 限制或監控常用於混淆的腳本直譯器與工具的使用。

---

## **TA0006: Credential Access (憑證存取)**

### **T1552.001: Credentials in Files (檔案中的憑證)**
-   **描述**: 攻擊者在受控的伺服器上搜索包含明文或弱加密憑證的檔案。
-   **關鍵徵象**:
    -   **檔案存取審計 (`auditd`)**: Web 服務程序（`www-data`）讀取了非預期的敏感設定檔，如 `wp-config.php`, `.env`, `/etc/shadow`, `~/.aws/credentials`。
    -   **Shell 歷史紀錄 (`.bash_history`)**: 包含 `cat`, `grep`, `find` 等指令，其目標為已知的憑證檔案。
-   **防禦/緩解**:
    -   `M1022`: 對憑證檔案設定嚴格的存取控制權限。
    -   `M1028`: 將敏感憑證儲存在安全的保管庫（Vault）中，而非明文存放在設定檔裡。

---

## **TA0040: Impact (影響)**

### **T1491.001: Defacement (網頁篡改)**
-   **描述**: 攻擊者修改網站的視覺外觀，替換為自己的內容，以達到破壞商譽、宣傳或抗議的目的。
-   **關鍵徵象**:
    -   **檔案完整性監控 (FIM)**: 網站核心檔案如 `index.html`, `index.php` 的內容被修改。
    -   **Web Server Log (`access.log`)**: 在網頁被篡改前，出現針對核心檔案的 `POST` 或 `PUT` 請求。
-   **防禦/緩解**:
    -   `M1053`: 維護關鍵資料的備份，以便在發生篡改後快速恢復。
    -   `M1022`: 對網站根目錄及核心檔案實施嚴格的寫入權限控制。

---

## **TA0007: Discovery (發現)**

### **T1082: System Information Discovery (系統資訊發現)**
-   **描述**: 攻擊者嘗試收集目標主機的詳細資訊，包括作業系統版本、硬體配置、主機名稱等，以便為後續的提權或橫向移動做準備。
-   **關鍵徵象**:
    -   **程序監控 (`auditd`, `Sysmon`)**: Web 服務程序（`www-data`）執行了系統資訊收集命令，如 `uname -a`, `lscpu`, `hostname`, `systeminfo`。
    -   **Web Shell 活動**: 透過 Web Shell 介面執行的指令日誌中包含上述系統命令。
-   **防禦/緩解**:
    -   `M1047`: 使用應用程式白名單或執行預防策略，限制 Web 服務帳號執行非必要的系統二進制檔案。
    -   `M1036`: 監控程序創建事件，特別是 Web 伺服器程序衍生的子程序，並對異常行為（如執行 `uname`）發出告警。

### **T1046: Network Service Discovery (網路服務發現)**
-   **描述**: 攻擊者探測內部網路，以識別可用的主機與服務，尋找潛在的橫向移動目標。
-   **關鍵徵象**:
    -   **程序監控**: Web 服務程序執行了網路掃描工具，如 `nmap`, `netstat -an`, `ss -tulpn`，或手動執行 `curl`, `telnet` 嘗試連接內部 IP 與埠口。
    -   **網路流量監控**: 從 Web 伺服器發起到內部其他主機的大量 TCP/UDP 連線嘗試，特別是針對常見服務埠口（如 22, 3306, 3389, 8080）的掃描行為。
-   **防禦/緩解**:
    -   `M1018`: 在主機層級使用防火牆（Host-based Firewall），限制 Web 伺服器的出站連線，僅允許必要的通訊。
    -   `M1036`: 監控 Web 伺服器發起的網路連線，對連接到大量內部 IP 或埠口的行為發出告警。

### **T1057: Process Discovery (程序發現)**
-   **描述**: 攻擊者列出在系統上運行的程序，以了解當前的系統活動、正在運行的服務（如資料庫、安全軟體）以及潛在的可利用目標。
-   **關鍵徵象**:
    -   **程序監控**: Web 服務程序執行了 `ps aux`, `tasklist`, `top` 等指令。
    -   **命令列日誌**: Shell 歷史紀錄或 Web Shell 命令日誌中包含程序列表指令。
-   **防禦/緩解**:
    -   `M1036`: 監控程序創建及其命令列參數，對 Web 伺服器執行 `ps` 或 `tasklist` 的行為產生告警。

---

## **TA0008: Lateral Movement (橫向移動)**

### **T1021.001: Remote Desktop Protocol (遠端桌面協定)**
-   **描述**: 在取得一個立足點（如 Web 伺服器）和有效憑證後，攻擊者可能使用 RDP 連接到內部網路中的其他 Windows 主機。
-   **關鍵徵象**:
    -   **網路流量監控**: 從 Web 伺服器發起到內部其他主機的、目的埠為 3389 的出站 TCP 連線。
    -   **Windows 安全日誌 (目標主機)**: 事件 ID `4624` (登入成功) 或 `4625` (登入失敗)，來源網路地址為 Web 伺服器的 IP。
-   **防禦/緩解**:
    -   `M1018`: 在 Web 伺服器上配置主機防火牆，阻擋非必要的出站 RDP 連線。
    -   `M1029`: 在內部伺服器上強制使用網路級別驗證 (NLA) 和多因素驗證 (MFA)。

### **T1021.002: SMB/Windows Admin Shares (SMB/Windows 管理共享)**
-   **描述**: 攻擊者利用伺服器訊息區塊 (SMB) 協定，存取遠端主機的管理共享（如 `C$`, `ADMIN$`），以進行檔案傳輸或遠端執行。
-   **關鍵徵象**:
    -   **網路流量監控**: 從 Web 伺服器發起到內部其他主機的、目的埠為 445 的出站 TCP 連線。
    -   **Windows 安全日誌 (目標主機)**: 事件 ID `5140` (網路共享物件被存取) 或 `5145` (詳細的共享存取)，來源為 Web 伺服器 IP。
-   **防禦/緩解**:
    -   `M1018`: 限制 Web 伺服器的出站 SMB 流量。
    -   `M1043`: 對於伺服器間的通訊，考慮停用不必要的管理共享。

---

## **TA0009: Collection (收集)**

### **T1005: Data from Local System (從本地系統收集資料)**
-   **描述**: 攻擊者從本地檔案系統中收集感興趣的資料，這些資料可能是後續竊取的目標。
-   **關鍵徵象**:
    -   **檔案存取審計 (`auditd`)**: Web 服務帳號讀取了大量檔案，或存取了非其正常工作範圍內的目錄，如 `/home`, `/var/lib/mysql`。
    -   **程序監控**: `www-data` 使用者執行了壓縮工具，如 `tar`, `zip`, `gzip`，將多個檔案或目錄打包成單一檔案。
-   **防禦/緩解**:
    -   `M1022`: 實施最小權限原則，確保 Web 服務帳號只能讀取其運行所需的最小檔案集合。
    -   `M1059`: 監控敏感目錄的檔案存取模式，對異常的大量讀取行為發出告警。

### **T1114.001: Local Email Collection (本地郵件收集)**
-   **描述**: 如果 Web 伺服器也運行郵件服務或儲存郵件檔案（如 `.pst`, `.mbox`)，攻擊者可能會嘗試收集這些郵件以獲取敏感資訊。
-   **關鍵徵象**:
    -   **檔案存取審計**: Web 服務帳號讀取了位於 `/var/mail/` 或使用者家目錄下的郵件儲存檔案。
-   **防禦/緩解**:
    -   `M1001`: 避免在面向公眾的 Web 伺服器上儲存敏感的郵件資料。
    -   `M1022`: 嚴格限制對郵件儲存目錄的檔案存取權限。

---

## **TA0010: Exfiltration (竊取)**

### **T1041: Exfiltration Over C2 Channel (透過 C2 通道竊取)**
-   **描述**: T攻擊者利用其已建立的命令與控制 (C2) 通道（例如，透過 Web Shell 的 HTTP/HTTPS 連線）來傳輸竊取出的資料，以此來混淆惡意流量與正常的 Web 流量。
-   **關鍵徵象**:
    -   **網路流量監控**:
        -   從 Web 伺服器到外部 IP 的 HTTP `POST` 請求中，其回應 Body 的大小異常巨大（例如，數十 MB 的壓縮檔）。
        -   DNS 查詢日誌顯示 Web 伺服器嘗試解析不常見或隨機生成的域名，可能用於 DNS 隧道竊取。
-   **防禦/緩解**:
    -   `M1037`: 實施流量分析，監控出站 Web 流量的基線，並對流量大小、頻率的異常情況發出告警。
    -   `M1020`: 使用 DNS 白名單或 Sinkhole 技術，阻止 Web 伺服器解析惡意或未授權的域名。

---

# OWASP Top 10 (2021) — Web Server/Application-Layer Attack Knowledge Base  
Last Updated: 2025-08-02 UTC+8

> Extracted from official OWASP documentation and consolidated with public research by Black Duck, Security Journey, and others. Each risk node includes: a core description, key indicators (mappable to logs), defense essentials, and an attack-flow example. Paragraphs are finely split to facilitate sentence vectorization before being ingested into Qdrant.

---

## Index
| Code | Risk Name |
|:---|:---|
| A01 | Broken Access Control |
| A02 | Cryptographic Failures |
| A03 | Injection |
| A04 | Insecure Design |
| A05 | Security Misconfiguration |
| A06 | Vulnerable and Outdated Components |
| A07 | Identification and Authentication Failures |
| A08 | Software and Data Integrity Failures |
| A09 | Security Logging and Monitoring Failures |
| A10 | Server-Side Request Forgery (SSRF) |

---

## A01 Broken Access Control  
Source stats: 34 CWEs, occurrence rate 55.97 % (OWASP) ([owasp.org](https://owasp.org/Top10/#a01-broken-access-control))

### Description  
The application fails to properly restrict authorization operations, allowing horizontal or vertical privilege escalation, IDOR, and forced browsing.

### Key Indicators (Logs)  
-  URLs containing `../`, `/admin/`, `/export?user=other`  
-  An unauthorized user first receives 401 → immediately followed by 200  
-  JWT or cookie payloads are tampered with

### Defense Essentials  
-  Default-deny posture with centralized RBAC  
-  Server-side revalidation of ID-to-resource mapping  
-  Signed JWTs with short TTL; CORS allow-list

### Example Attack Flow  
1. The attacker logs in with a normal account `user=101`.  
2. They access `/api/users/102/profile` → 200 response.  
3. Personal data is stolen; the SIEM observes the same token traversing multiple userIds.  
4. SOAR: temporarily lock the account → notify the DPO.

---

## A02 Cryptographic Failures  
Focus: improper encryption/decryption, use of HTTP, weak TLS ([owasp.org](https://owasp.org/Top10/#a02-cryptographic-failures))

### Description  
Sensitive data is transmitted or stored unencrypted, or protected with outdated algorithms.

### Key Indicators  
-  Logs show `GET http://` sending `Set-Cookie: sessionid=`  
-  TLS v1 handshake or self-signed certificate

### Defense Essentials  
-  Enforce HSTS and TLS 1.3  
-  Use a trusted CA; set Secure and SameSite attributes

### Example Attack Flow  
1. A user logs in over public Wi-Fi; packets reveal a plaintext cookie.  
2. The attacker replays the cookie to hijack the session.

---

## A03 Injection  
Stats: 33 CWEs; total incidents 274 k + ([owasp.org](https://owasp.org/Top10/#a03-injection))

### Description  
Unvalidated input is injected into an interpreter such as SQL, OS, LDAP, NoSQL, or a browser (XSS).

### Key Indicators  
-  `UNION SELECT` or `OR 1=1` appears in URI or body  
-  Database error `syntax near ...` with 500 response  
-  Delayed responses (time-based blind injection)

### Defense Essentials  
-  Prepared statements or ORM  
-  Strict allow-list validation  
-  Code review plus SAST/DAST

### Example Attack Flow (classic SQLi → web shell)  
1. `/product?id=1 UNION SELECT password FROM users--` triggers 500.  
2. After dumping hashes, `/upload.php` is used to upload `shell.php`.  
3. Backdoor accessed via `/uploads/shell.php`; Nginx 200 with an atypical User-Agent.

---

## A04 Insecure Design  
Design lacks threat modeling and rate limiting ([owasp.org](https://owasp.org/Top10/#a04-insecure-design))

### Key Indicators  
-  Single IP sends > 100 req/s and still receives 200 responses  
-  No CSRF token present

### Defense Essentials  
-  Perform STRIDE threat modeling early in development  
-  Apply global rate limiting or circuit breakers

---

## A05 Security Misconfiguration  
CIS Benchmark drift and default credentials ([owasp.org](https://owasp.org/Top10/#a05-security-misconfiguration))

### Key Indicators  
-  `/server-status` returns 200  
-  `.git/HEAD` is downloadable

### Defense Essentials  
-  Establish IaC baselines and run configuration scanners (e.g., ScoutSuite)

---

## A06 Vulnerable and Outdated Components  
Third-party package flaws, Log4Shell vulnerability ([owasp.org](https://owasp.org/Top10/#a06-vulnerable-and-outdated-components))

### Key Indicators  
-  `wpscan` scanning User-Agent  
-  Requests to `/wp-json` or `/.env`

### Defense Essentials  
-  Maintain an SBOM and enable Dependabot or similar auto-updates

---

## A07 Identification and Authentication Failures  
Brute-force attacks and session fixation ([owasp.org](https://owasp.org/Top10/#a07-identification-and-authentication-failures))

### Key Indicators  
-  Spike in 401 responses on `/wp-login.php`  
-  Same IP attempts multiple accounts

### Defense Essentials  
-  Enforce MFA and deploy fail2ban

### Example Attack Flow (SSH + MySQL brute force)  
1. Within 30 seconds, 100 + `Access denied for user 'root'@` events occur.  
2. SIEM raises an alert; SOAR action: apply iptables DROP.

---

## A08 Software and Data Integrity Failures  
CI/CD artifacts are tampered with ([owasp.org](https://owasp.org/Top10/#a08-software-and-data-integrity-failures))

### Key Indicators  
-  New JavaScript lacks SRI  
-  Unsigned container images

---

## A09 Security Logging and Monitoring Failures  
Events go unlogged or alerts are delayed ([owasp.org](https://owasp.org/Top10/#a09-security-logging-and-monitoring-failures))

### Key Indicators  
-  5xx responses without stack trace; logs missing Referer/User-Agent  
-  SIEM cannot correlate the attack chain

---

## A10 Server-Side Request Forgery (SSRF)  
New entrant; high risk in cloud environments ([owasp.org](https://owasp.org/Top10/#a10-server-side-request-forgery-ssrf))

### Description  
The application allows users to supply a URL that the server then requests without verification, potentially targeting intranet or metadata endpoints.

### Key Indicators  
-  URLs containing `169.254.169.254` or `127.0.0.1`  
-  5xx responses and variable time-outs

### Defense Essentials  
-  URL allow-list and block intranet IP ranges  
-  Outbound (egress) firewall

### Example Attack Flow (cloud IAM key leak)  
1. The image-upload feature is abused to request `http://169.254.169.254/latest/meta-data/iam/`.  
2. The server returns IAM information; the attacker obtains temporary credentials.  
3. SOAR: immediately rotate keys → block the internal address.

---

## References
-  OWASP Top 10 2021 official site ([owasp.org](https://owasp.org/Top10/))  
-  OWASP Proactive Controls & Cheat Sheet Series ([owasp.org](https://owasp.org/www-project-proactive-controls/))  
-  Black Duck CyRC — OWASP Top 10 Analysis Report 2023 ([blackduck.com](https://www.blackduck.com))  
-  Security Journey Blog: Broken Access Control Explained ([securityjourney.com](https://www.securityjourney.com/post/owasp-top-10-broken-access-control-explained))

---

# OWASP Top 10 (2021) — 專注於 Web Server/應用層之攻擊知識庫  
最後更新：2025-08-02 UTC+8

> 摘自 OWASP 官方文件並整合 Black Duck、Security Journey 等公開研究。每一風險節點皆含：核心描述、關鍵徵象（可映射到 Log）、防禦要點、案例流程。段落精細分拆，便於斷句向量化後餵入 Qdrant。

---

## 索引
| 代號 | 風險名稱 |
|:---|:---|
| A01 | Broken Access Control |
| A02 | Cryptographic Failures |
| A03 | Injection |
| A04 | Insecure Design |
| A05 | Security Misconfiguration |
| A06 | Vulnerable & Outdated Components |
| A07 | Identification & Authentication Failures |
| A08 | Software & Data Integrity Failures |
| A09 | Security Logging & Monitoring Failures |
| A10 | Server-Side Request Forgery (SSRF) |

---

## A01 Broken Access Control  
來源統計：34 個 CWE，發生率 55.97 %（OWASP）([owasp.org](https://owasp.org/Top10/#a01-broken-access-control))

### 描述  
應用未正確限制身分操作，允許水平/垂直越權、IDOR、強制瀏覽。

### 關鍵徵象 (Log)  
-  URL 含 `../`、`/admin/`、`/export?user=other`  
-  非授權 user 先 401→隨即 200  
-  JWT / Cookie payload 被竄改

### 防禦要點  
-  「預設拒絕」+ 中央 RBAC  
-  伺服器端再驗證 ID 與資源對照  
-  JWT 加簽、短 TTL、CORS allowlist

### 案例流程  
1. 攻擊者登入一般帳號 `user=101`  
2. 直接存取 `/api/users/102/profile` → 200 回應  
3. 盜取他人個資；SIEM 觀察到相同 token 穿梭多個 userId  
4. SOAR：暫鎖帳號→通知 DPO

---

## A02 Cryptographic Failures  
重點：不當加解密、使用 HTTP、弱 TLS([owasp.org](https://owasp.org/Top10/#a02-cryptographic-failures))

### 描述  
敏感資料傳輸/儲存未加密或使用過期演算法。

### 關鍵徵象  
-  Log 顯示 `GET http://` 傳送 `Set-Cookie: sessionid=`  
-  TLSv1 握手、Self-Signed Cert

### 防禦  
-  HSTS、TLS 1.3  
-  使用可信 CA、設定 Secure & SameSite

### 案例流程  
1. 使用者於公共 Wi-Fi 登入，封包抓到明文 Cookie  
2. 攻擊者重播 Cookie 即可劫持 Session

---

## A03 Injection  
統計：33 CWE；總事件 274 k +([owasp.org](https://owasp.org/Top10/#a03-injection))

### 描述  
未過濾輸入被注入至解譯器：SQL/OS/LDAP/NoSQL/XSS。

### 關鍵徵象  
-  `UNION SELECT`、`OR 1=1` 出現在 URI/Body  
-  DB error `syntax near ...` 500 回應  
-  延遲回應 (時間盲注)

### 防禦  
-  Prepared-Statement / ORM  
-  嚴格白名單驗證  
-  程式碼審查 + SAST/DAST

### 案例流程：經典 SQLi → WebShell  
1. `/product?id=1 UNION SELECT password FROM users--` 觸發 500  
2. Dump 出 hash 後利用 `/upload.php` 上傳 `shell.php`  
3. 後門存取 `/uploads/shell.php`；Nginx 200 + 非典型 UA

---

## A04 Insecure Design  
設計缺少威脅建模、速率限制([owasp.org](https://owasp.org/Top10/#a04-insecure-design))

### 關鍵徵象  
-  單 IP 每秒 >100 req 仍 200  
-  無 csrf token

### 防禦  
-  開發初期做威脅建模（STRIDE）  
-  全域限流 / circuit breaker

---

## A05 Security Misconfiguration  
CIS Benchmark 偏差、預設帳密([owasp.org](https://owasp.org/Top10/#a05-security-misconfiguration))

### 關鍵徵象  
-  `/server-status` 200  
-  `.git/HEAD` 可下載

### 防禦  
-  IaC baseline、掃描器 (ScoutSuite)

---

## A06 Vulnerable & Outdated Components  
第三方套件漏洞、Log4Shell([owasp.org](https://owasp.org/Top10/#a06-vulnerable-and-outdated-components))

### 關鍵徵象  
-  `wpscan` 掃描 UA  
-  `/wp-json`、`/.env`

### 防禦  
-  SBOM、Dependabot 自動更新

---

## A07 Identification & Authentication Failures  
暴力破解、Session Fixation([owasp.org](https://owasp.org/Top10/#a07-identification-and-authentication-failures))

### 關鍵徵象  
-  `/wp-login.php` 401 激增  
-  同 IP 嘗試多帳號

### 防禦  
-  MFA、fail2ban

### 案例流程：SSH + MySQL Bruteforce  
1. 30s 內 100+ `Access denied for user 'root'@`  
2. SIEM 提醒；SOAR 動作：iptables DROP

---

## A08 Software & Data Integrity Failures  
CI/CD 產物被竄改([owasp.org](https://owasp.org/Top10/#a08-software-and-data-integrity-failures))

### 關鍵徵象  
-  新 JS 未含 SRI  
-  未簽名容器映像

---

## A09 Security Logging & Monitoring Failures  
事件無記錄、告警延遲([owasp.org](https://owasp.org/Top10/#a09-security-logging-and-monitoring-failures))

### 關鍵徵象  
-  5xx 無 stack trace、Log 缺 Referer/UA  
-  SIEM 無法關聯攻擊鏈

---

## A10 Server-Side Request Forgery (SSRF)  
新進榜項目，雲場域高風險([owasp.org](https://owasp.org/Top10/#a10-server-side-request-forgery-ssrf))

### 描述  
應用讓使用者指定 URL，未驗證即由伺服器發出，可能打到內網／Metadata。

### 關鍵徵象  
-  URL 包含 `127.0.0.1`  
-  回應 5xx、超時變動

### 防禦  
-  URL allowlist、禁止內網 IP  
-  egress firewall

### 案例流程：雲端 IAM key 洩漏  
1. 上傳圖片功能被改傳 `http://169.254.169.254/latest/meta-data/iam/`  
2. 伺服器回傳 IAM 資訊；攻擊者取得暫時認證  
3. SOAR：立刻 rotate key→封鎖內部地址

---

## 參考資料
-  OWASP Top 10 2021 官方網站 ([owasp.org](https://owasp.org/Top10/))  
-  OWASP Proactive Controls & Cheat Sheet Series ([owasp.org](https://owasp.org/www-project-proactive-controls/))  
-  Black Duck CyRC — OWASP Top 10 分析報告 2023 ([blackduck.com](https://www.blackduck.com))  
-  Security Journey Blog: Broken Access Control Explained ([securityjourney.com](https://www.securityjourney.com/post/owasp-top-10-broken-access-control-explained))

---
