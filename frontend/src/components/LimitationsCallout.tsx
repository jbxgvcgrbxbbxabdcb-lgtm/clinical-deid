/** Caveats for operators before trusting a redaction pass. */

type LimitItem = { tag: string; text: string };

const ITEMS: LimitItem[] = [
  {
    tag: "合成",
    text: "仅用于合成 / 演示数据，请勿上传真实 PHI。",
  },
  {
    tag: "中文",
    text: "模型仅支持英文文件脱敏，中文主要靠系统规则与自定义。",
  },
  {
    tag: "Word",
    text: "已支持常见文本框写回；SmartArt、修订/批注、部分复杂控件仍可能漏检。",
  },
  {
    tag: "PDF",
    text: "仅支持有文本层的非扫描件；扫描件暂不支持。",
  },
  {
    tag: "规则",
    text: "修改「必脱敏 / 勿脱敏」或脱敏方法后会重新检测，请稍候加载完成再点应用。",
  },
  {
    tag: "复核",
    text: "请人工核对列表；规则也可能误报，取消勾选即可排除。",
  },
];

export function LimitationsCallout() {
  return (
    <details className="limits-callout">
      <summary>
        <span className="limits-summary-main">
          <span className="limits-kicker" aria-hidden="true">
            Note
          </span>
          <span className="limits-title">使用注意</span>
          <span className="limits-sub">操作前请阅读</span>
        </span>
        <span className="chev" aria-hidden="true">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </span>
      </summary>
      <ul className="limits-list">
        {ITEMS.map((item) => (
          <li key={item.tag}>
            <span className="limits-tag">{item.tag}</span>
            <span className="limits-text">{item.text}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}
