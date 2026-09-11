# Clash-SKK MRS

[SukkaW/Surge](https://github.com/SukkaW/Surge) 规则集的自动镜像：保留 [Paxxs/clash-skk](https://github.com/Paxxs/clash-skk) 生成的 YAML rule-provider，并生成 Mihomo 可用的 MRS 二进制规则集。

## 自动更新

GitHub Actions 每日 03:00、15:00 UTC 从 `https://ruleset.skk.moe` 拉取规则：

- `Clash/`：YAML rule-provider，沿用上游的全部输出。
- `MRS/domainset/`：`behavior: domain` 的 `.mrs`。
- `MRS/ip/`：`behavior: ipcidr` 的 `.mrs`。

MRS 格式只支持 `domain` 和 `ipcidr`。`Clash/non_ip/` 中的 `classical` 规则不生成 MRS，继续用 YAML。

## Mihomo 配置

```yaml
rule-providers:
  reject_domain:
    type: http
    behavior: domain
    format: mrs
    interval: 43200
    url: https://cdn.jsdelivr.net/gh/cccClyde/clash-skk@main/MRS/domainset/reject.mrs
    path: ./ruleset/reject.mrs

  china_ip:
    type: http
    behavior: ipcidr
    format: mrs
    interval: 43200
    url: https://cdn.jsdelivr.net/gh/cccClyde/clash-skk@main/MRS/ip/china_ip.mrs
    path: ./ruleset/china_ip.mrs

rules:
  - RULE-SET,reject_domain,REJECT
  - RULE-SET,china_ip,DIRECT,no-resolve
```

`domainset` 与 `ip` 目录中含有可用 payload 的来源都会生成同路径名 `.mrs`；`ip` 中只含域名或其他 classical 条目的文件会跳过。例如：

- `https://cdn.jsdelivr.net/gh/cccClyde/clash-skk@main/MRS/domainset/ai.mrs`
- `https://cdn.jsdelivr.net/gh/cccClyde/clash-skk@main/MRS/ip/telegram.mrs`

## blackmatrix7：WeChat 和 YouTube

工作流还会同步 [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) 的 WeChat、YouTube 规则：

- 原始完整 classical YAML：`Clash/blackmatrix7/WeChat.yaml`、`Clash/blackmatrix7/YouTube.yaml`。
- MRS：`MRS/blackmatrix7/WeChat-domain.mrs`、`YouTube-domain.mrs`、`YouTube-ip.mrs`。

MRS 只支持 domain、ipcidr：WeChat 的 `IP-ASN,132203` 与 YouTube 的 `DOMAIN-KEYWORD,youtube` 会保留在镜像 YAML，不能等价转换到 MRS。

```yaml
rule-providers:
  wechat_domain:
    type: http
    behavior: domain
    format: mrs
    interval: 43200
    url: https://cdn.jsdelivr.net/gh/cccClyde/clash-skk@main/MRS/blackmatrix7/WeChat-domain.mrs
    path: ./ruleset/WeChat-domain.mrs
  youtube_domain:
    type: http
    behavior: domain
    format: mrs
    interval: 43200
    url: https://cdn.jsdelivr.net/gh/cccClyde/clash-skk@main/MRS/blackmatrix7/YouTube-domain.mrs
    path: ./ruleset/YouTube-domain.mrs
  youtube_ip:
    type: http
    behavior: ipcidr
    format: mrs
    interval: 43200
    url: https://cdn.jsdelivr.net/gh/cccClyde/clash-skk@main/MRS/blackmatrix7/YouTube-ip.mrs
    path: ./ruleset/YouTube-ip.mrs

rules:
  - RULE-SET,wechat_domain,DIRECT
  - IP-ASN,132203,DIRECT
  - RULE-SET,youtube_domain,代理
  - DOMAIN-KEYWORD,youtube,代理
  - RULE-SET,youtube_ip,代理,no-resolve
```

如需 WeChat 的 IP-ASN 或 YouTube 的 keyword 规则也统一作为 rule-provider 使用，直接引用 `Clash/blackmatrix7/*.yaml` 并使用 `behavior: classical`。

## 本地执行

需要 Go 和 Mihomo：

```bash
go build -o bin/clash-skk ./cmd/clash-skk
MIHOMO_BIN=/path/to/mihomo ./scripts/update-rules.sh
```

转换命令等价于：

```bash
mihomo convert-ruleset domain yaml Clash/domainset/reject.yaml MRS/domainset/reject.mrs
mihomo convert-ruleset ipcidr yaml Clash/ip/china_ip.yaml MRS/ip/china_ip.mrs
```
