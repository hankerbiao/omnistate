/**
 * 登录 API 测试脚本
 *
 * 用法:
 * 1. 确保后端服务已启动 (http://localhost:8000)
 * 2. 在浏览器控制台中运行此脚本
 * 3. 查看测试结果
 */

// 后端 API 基础 URL
const API_BASE = 'http://localhost:8000/api/v1';

// 测试账户
const TEST_ACCOUNTS = [
  { user_id: 'admin', password: '123456', description: '管理员' },
  { user_id: 'alice', password: '123456', description: 'Alice' },
  { user_id: 'bob', password: '123456', description: 'Bob' },
];

console.log('🚀 开始测试登录 API...\n');

// 测试登录函数
async function testLogin(account) {
  try {
    console.log(`\n📝 测试账户: ${account.description} (${account.user_id})`);
    console.log('   发送登录请求...');

    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: account.user_id,
        password: account.password,
      }),
    });

    const result = await response.json();

    if (response.ok && result.code === 200) {
      console.log('   ✅ 登录成功!');
      console.log('   📦 响应数据:');
      console.log('      - access_token:', result.data.access_token.substring(0, 50) + '...');
      console.log('      - user_id:', result.data.user.user_id);
      console.log('      - username:', result.data.user.username);
      console.log('      - status:', result.data.user.status);

      // 测试使用令牌获取用户信息
      console.log('\n   🔑 测试获取当前用户信息...');
      const userResponse = await fetch(`${API_BASE}/auth/users/me`, {
        headers: {
          'Authorization': `Bearer ${result.data.access_token}`,
        },
      });

      if (userResponse.ok) {
        const userData = await userResponse.json();
        console.log('   ✅ 获取用户信息成功!');
        console.log('      用户详情:', userData.data);
      } else {
        console.log('   ⚠️ 获取用户信息失败:', userResponse.status);
      }

      return true;
    } else {
      console.log('   ❌ 登录失败!');
      console.log('      状态码:', response.status);
      console.log('      错误信息:', result.message || result.detail || '未知错误');
      return false;
    }
  } catch (error) {
    console.log('   ❌ 请求异常:', error.message);
    console.log('      可能原因: 后端服务未启动或 URL 错误');
    return false;
  }
}

// 执行测试
async function runTests() {
  console.log('='.repeat(60));
  console.log('登录 API 功能测试');
  console.log('='.repeat(60));

  let successCount = 0;
  let failCount = 0;

  for (const account of TEST_ACCOUNTS) {
    const success = await testLogin(account);
    if (success) {
      successCount++;
    } else {
      failCount++;
    }
  }

  console.log('\n' + '='.repeat(60));
  console.log('测试完成!');
  console.log('='.repeat(60));
  console.log(`✅ 成功: ${successCount}/${TEST_ACCOUNTS.length}`);
  console.log(`❌ 失败: ${failCount}/${TEST_ACCOUNTS.length}`);

  if (failCount === TEST_ACCOUNTS.length) {
    console.log('\n⚠️ 所有登录测试都失败了，请检查:');
    console.log('   1. 后端服务是否已启动 (http://localhost:8000)');
    console.log('   2. 测试账户是否已创建');
    console.log('   3. CORS 配置是否正确');
  }

  console.log('\n📚 测试说明:');
  console.log('   - 这个脚本测试了前端登录 API 的基本功能');
  console.log('   - 包括登录请求和令牌验证');
  console.log('   - 如果所有测试通过，说明后端 API 可以正常使用');
}

// 运行测试
runTests().catch(console.error);