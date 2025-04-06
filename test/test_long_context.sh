#!/bin/bash

# 设置环境变量
API_BASE_URL="http://localhost:8000"
API_KEY="test-key"  # 替换为实际的 API key

# 定义用法信息
usage() {
  echo "用法: $0 [选项]"
  echo "选项:"
  echo "  -m, --model <name>  指定模型名称 (默认: multi_agent)"
  echo "  -h, --help          显示此帮助信息"
  exit 1
}

# 默认参数
MODEL_NAME="multi_agent"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    -m|--model)
      MODEL_NAME="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "未知选项: $1"
      usage
      ;;
  esac
done

# 读取长上下文JSON文件
LONG_CONTEXT_FILE="./data/long_context.json"
if [ ! -f "$LONG_CONTEXT_FILE" ]; then
  echo "错误: 找不到长上下文文件 $LONG_CONTEXT_FILE"
  exit 1
fi

# 读取文件内容并替换model字段
LONG_CONTEXT_JSON=$(cat "$LONG_CONTEXT_FILE" | sed "s/\"model\": \"[^\"]*\"/\"model\": \"${MODEL_NAME}\"/")

# 打印测试信息
echo "===== 开始测试长上下文对话 ====="
echo "使用模型: ${MODEL_NAME}"
echo "请求大小: $(echo "$LONG_CONTEXT_JSON" | wc -c) 字节"
echo "消息数量: $(echo "$LONG_CONTEXT_JSON" | grep -o "\"role\":" | wc -l)"
echo "==============================="

# 执行测试请求
echo "发送长上下文请求..."
echo "结果将保存到 long_context_response.txt"

# 添加stream=false以获取完整响应而非流式响应
LONG_CONTEXT_JSON=$(echo "$LONG_CONTEXT_JSON" | sed 's/"stream": true/"stream": false/')

curl -X POST "${API_BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "${LONG_CONTEXT_JSON}" > long_context_response.txt

# 检查请求结果
if [ $? -eq 0 ]; then
  echo "测试完成！"
  echo "响应大小: $(wc -c < long_context_response.txt) 字节"
  echo "您可以查看 long_context_response.txt 获取完整响应"
else
  echo "测试失败：请求过程中出现错误"
  exit 1
fi

# 尝试提取模型的响应（如果是JSON格式）
if grep -q "\"choices\":" long_context_response.txt; then
  echo ""
  echo "模型响应摘要:"
  # 提取模型回复的前100个字符作为摘要
  RESPONSE_PREVIEW=$(grep -o '"content":"[^"]*"' long_context_response.txt | head -1 | sed 's/"content":"//;s/"$//' | head -c 100)
  echo "$RESPONSE_PREVIEW..."
  echo ""
  
  # 检查是否有错误信息
  if grep -q "\"error\":" long_context_response.txt; then
    echo "警告: 响应中包含错误信息!"
    grep -A 5 "\"error\":" long_context_response.txt
  fi
fi

echo "===== 长上下文测试结束 =====" 