#!/bin/bash

# 设置环境变量
API_BASE_URL="http://localhost:8000"
API_KEY="test-key"  # 替换为实际的 API key

# 定义用法信息
usage() {
  echo "用法: $0 [选项]"
  echo "选项:"
  echo "  -t, --test <case>   指定测试用例 (counseling, simple)"
  echo "  -m, --model <name>  指定模型名称 (默认: multi_agent)"
  echo "  -h, --help          显示此帮助信息"
  exit 1
}

# 默认参数
TEST_CASE="all"
MODEL_NAME="multi_agent2"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    -t|--test)
      TEST_CASE="$2"
      shift 2
      ;;
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

# 心理咨询案例的 JSON 数据
COUNSELING_JSON=$(cat << EOF
{
  "model": "${MODEL_NAME}",
  "stream": true,
  "messages": [
    {
      "role": "user",
      "content": "**案例报告：**\n女，19岁，独女，初中未毕业（初三休学后不能再复学），1.65m，长相一般，肤白，长发，家住本市。\n来诊经过：精神科住院病人，出院后做心理治疗。\n症状：2019年上初三的时候生病，情绪低，自残行为，当时住院治疗。因为病情反复波动，情绪高低起伏，情绪变化大，有时兴奋有时又很低落，后诊断为\"双相情感障碍，快速循环型\"，前后多次住院，吃过多种药物效果不佳。\n成长经历\n自小在父母身边长大，自小成绩好，很小就开始上各种辅导班，如幼儿园时上拼音班，上小学后英语班，作文班，数学班，奥数班，愿意上，能给自己带来情绪价值，小学时班长，班里各种活动都过问，获奖很多。在5、6年级时班里转过来一个女生（现在上南京体校），女生妈妈在班级群里发女生获得的奖状，不久女生就跟老师关系亲近，来访者心里面难受，加之女生贬低自己长得不好看，因为开始对自己长相不满。\n初中上某中学的分校，年级200人，初一排名前20名，初一开始出现胃痛，不厉害。初二成绩下降明显，写作业晚，有时要写到半夜2、3点，到早晨5、6点就醒。初中当学生会会长，管各种事情，班级文艺演出编排等，（休学后原来班级老师还打电话请来访者为他们演出编节目。）自己付出很多却感觉有个别人不配合，老师各种事情都要来访者做，但又批评其成绩下降，心情不好，有自残行为，用圆规戳手指流血，流血后心里会感觉好受一点。但是老师家长都不觉得其有问题，认为自己调一下就行了，直到初三下崩不住了看四院休学。住院3次，在北大六院住院一次。因为病情反复的波动，所以在主管医生建议下做心理治疗。\n习惯好的感觉不能接受不好的感觉，体育是弱项，每次上体育课前或头天晚上注意力不集中或睡不着。"
    }
  ]
}
EOF
)

# 简单问候的 JSON 数据
SIMPLE_JSON=$(cat << EOF
{
  "model": "${MODEL_NAME}",
  "stream": true,
  "messages": [
    {"role": "user", "content": "你好，我想你帮助我做一个心理咨询案例。"}
  ]
}
EOF
)

# 测试心理咨询案例
run_counseling_test() {
  echo "测试心理咨询案例..."
  curl -X POST "${API_BASE_URL}/v1/chat/completions" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "${COUNSELING_JSON}"
  echo -e "\n测试完成\n"
}

# 测试简单问候
run_simple_test() {
  echo "测试简单问候..."
  curl -X POST "${API_BASE_URL}/v1/chat/completions" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "${SIMPLE_JSON}"
  echo -e "\n测试完成\n"
}

# 根据参数运行测试
case "${TEST_CASE}" in
  "counseling")
    run_counseling_test
    ;;
  "simple")
    run_simple_test
    ;;
  "all")
    run_counseling_test
    run_simple_test
    ;;
  *)
    echo "未知测试用例: ${TEST_CASE}"
    usage
    ;;
esac
