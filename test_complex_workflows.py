from db.relational import init_db, init_mock_config, get_session
from services.workflow_service import WorkflowService
from core.logger import log

def test_requirement_workflow(service: WorkflowService):
    """
    测试需求业务流程：
    创建需求 -> 提交并指定审核人 -> 审核通过
    """
    log.info(">>> 开始测试 [需求] 业务流程")
    
    # 1. 创建需求
    item = service.create_item(
        type_code="REQUIREMENT",
        title="支付系统重构",
        content="需要支持多渠道支付",
        creator_id=1
    )
    
    # 2. 提交并指定审核人 (ID: 88)
    item = service.handle_transition(
        work_item_id=item.id,
        action="SUBMIT",
        operator_id=1,
        form_data={"priority": "P0", "target_owner_id": 88}
    )
    
    # 3. 审核人通过
    item = service.handle_transition(
        work_item_id=item.id,
        action="APPROVE",
        operator_id=88,
        form_data={"comment": "逻辑清晰，准予执行"}
    )
    
    log.success(f"--- [需求] 流程测试通过，最终状态: {item.current_state} ---")

def test_testcase_workflow(service: WorkflowService):
    """
    测试用例业务流程：
    创建用例 -> 指派用例 -> 开始开发 -> 完成开发 -> 审核通过
    """
    log.info(">>> 开始测试 [测试用例] 业务流程")
    
    # 1. 创建测试用例
    item = service.create_item(
        type_code="TEST_CASE",
        title="用户登录冒烟测试",
        content="验证手机号+验证码登录逻辑",
        creator_id=1
    )
    
    # 2. 指派给开发人员 (ID: 7)
    item = service.handle_transition(
        work_item_id=item.id,
        action="ASSIGN",
        operator_id=1,
        form_data={"target_owner_id": 7}
    )
    
    # 3. 开发人员开始开发
    item = service.handle_transition(
        work_item_id=item.id,
        action="START_DEVELOP",
        operator_id=7,
        form_data={}
    )
    
    # 4. 完成开发并提交评审，指定评审人 (ID: 9)
    item = service.handle_transition(
        work_item_id=item.id,
        action="FINISH_DEVELOP",
        operator_id=7,
        form_data={"target_owner_id": 9}
    )
    
    # 5. 评审人通过
    item = service.handle_transition(
        work_item_id=item.id,
        action="APPROVE",
        operator_id=9,
        form_data={"comment": "用例覆盖全面"}
    )
    
    log.success(f"--- [测试用例] 流程测试通过，最终状态: {item.current_state} ---")

def run_tests():
    # 初始化环境
    init_db()
    with get_session() as session:
        # 初始化基础数据
        init_mock_config(session)
        
        # 实例化服务
        service = WorkflowService(session)
        
        # 执行测试
        try:
            test_requirement_workflow(service)
            print("\n" + "="*50 + "\n")
            test_testcase_workflow(service)
        except Exception as e:
            log.exception(f"测试执行出错: {e}")
        finally:
            session.commit()

if __name__ == "__main__":
    run_tests()
