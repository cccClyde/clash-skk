# Clash-SKK MRS / SRS

[SukkaW/Surge](https://github.com/SukkaW/Surge) 规则集的自动镜像：保留 [Paxxs/clash-skk](https://github.com/Paxxs/clash-skk) 生成的 YAML rule-provider，生成 Mihomo 可用的 MRS 二进制规则集，以及 sing-box 可用的 SRS 二进制规则集。

## 自动更新

GitHub Actions 每日 03:00、15:00 UTC 从 `https://ruleset.skk.moe` 拉取规则：

- `Clash/`：YAML rule-provider，沿用上游的全部输出。
- `MRS/domainset/`：`behavior: domain` 的 `.mrs`。
- `MRS/ip/`：`behavior: ipcidr` 的 `.mrs`。
- `SingBox/source/`：上游 `sing-box/` 目录的 source JSON 原样镜像。
- `SingBox/srs/`：用 [reF1nd/sing-box](https://github.com/reF1nd/sing-box-releases) 最新正式版 `rule-set compile` 编译的 `.srs`。

MRS 格式只支持 `domain` 和 `ipcidr`。`Clash/non_ip/` 中的 `classical` 规则不生成 MRS，继续用 YAML。SRS 没有这个限制，上游每个 sing-box 规则集都有对应的 `.srs`。

## sing-box 配置

`SingBox/srs/` 与 `https://ruleset.skk.moe/sing-box/` 同目录结构，只是扩展名换成 `.srs`：

```json
{
  "route": {
    "rule_set": [
      {
        "type": "remote",
        "tag": "nonip_global",
        "format": "binary",
        "url": "https://cdn.jsdelivr.net/gh/cccClyde/clash-skk@main/SingBox/srs/non_ip/global.srs",
        "update_interval": "24h"
      },
      {
        "type": "remote",
        "tag": "ip_china_ip",
        "format": "binary",
        "url": "https://cdn.jsdelivr.net/gh/cccClyde/clash-skk@main/SingBox/srs/ip/china_ip.srs",
        "update_interval": "24h"
      }
    ]
  }
}
```

每次更新后 `scripts/verify-singbox-srs.py` 会把每个 `.srs` 反编译，与 source JSON 按匹配语义比对（相邻 CIDR 合并、已被 `domain_suffix` 覆盖的 `domain` 去重视为等价），不一致时工作流失败、不提交。

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

需要 Go、Mihomo 和 sing-box（建议 reF1nd 版）：

```bash
go build -o bin/clash-skk ./cmd/clash-skk
MIHOMO_BIN=/path/to/mihomo ./scripts/update-rules.sh
SING_BOX_BIN=/path/to/sing-box ./scripts/update-singbox-rules.py
SING_BOX_BIN=/path/to/sing-box ./scripts/verify-singbox-srs.py
```

转换命令等价于：

```bash
mihomo convert-ruleset domain yaml Clash/domainset/reject.yaml MRS/domainset/reject.mrs
mihomo convert-ruleset ipcidr yaml Clash/ip/china_ip.yaml MRS/ip/china_ip.mrs
```
