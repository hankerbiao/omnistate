import requests
import urllib3

# 消除使用 verify=False 产生的警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_worklog_tasks(uid, start_date, end_date, token=""):
    """
    获取指定用户和日期范围的工作日志任务
    :param uid: 用户ID (str 或 int)
    :param start_date: 开始日期 (格式: 'YYYY-MM-DD')
    :param end_date: 结束日期 (格式: 'YYYY-MM-DD')
    :param token: remember_token，默认为空
    :return: 接口返回的 JSON 数据，若失败则返回 None
    """
    url = "http://tl.cooacloud.com/worklog/tasks"

    params = {
        'timeshift': '-480',
        'uid': str(uid),
        'from': start_date,
        'to': end_date
    }

    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'Referer': 'http://tl.cooacloud.com/worklog/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }

    cookies = {'remember_token': token}

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            verify=False
        )
        response.raise_for_status()  # 检查 HTTP 请求是否成功
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None


# --- 调用示例 ---
if __name__ == "__main__":
    token = 'remember_token=libiao1|348082ba1e019ecfe9337b6962a9b4f2510418b7d45226aa4c0ceb51d4de88211f5986f86b1fb392402571a2f7120b2f44802c730f9279500742630283c51acd; check_box=true; access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc1MTMzNDM4MywianRpIjoiZDFlYTRiYTktYWU5MS00NzA4LTg3MTEtNzhkOTA4MmNjZmYzIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6ImxpYmlhbzEiLCJuYmYiOjE3NTEzMzQzODMsImV4cCI6MTc1MTkzOTE4MywibmFtZSI6Ilx1Njc0ZVx1NWY2YSIsImdyb3VwIjoyLCJyb2xlcyI6W10sInN0YXR1cyI6Ilx1NTcyOFx1ODA0YyIsImFkbWluIjpmYWxzZX0.cCk0WYulaRoYMtud-4phXLmERKIS4RncPSbhZ8LKgRQ; refresh_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc1MTMzNDM4MywianRpIjoiMDM0ZjY3YTUtMjU3Yi00YmE3LTgzNTItNTc2NzNlZTA1YWI1IiwidHlwZSI6InJlZnJlc2giLCJzdWIiOiJsaWJpYW8xIiwibmJmIjoxNzUxMzM0MzgzLCJleHAiOjE3NjY4ODYzODN9.tYllfAwkRjPtH6RUIotsSM3wgxKSOA9-adQbktHFhLU; s_dmlv3_251=4RkAizhrZHn0-eWxDpjLjqHTPxG4pTydRvm_FxuJZ7I; ass_secret=mbbyKyOTzrngT353MTB51cVQSoCtAxgr; DP_Token=1958ef7f-3b90-4115-b634-0462bb6efbe3; session=.eJwlzksKwzAMANG7eN2FJFtSnMsU62MaKBSSZlV69wZ6gZn3Kfe55_Eo63s_81buW5S15OiRFE4i6oIMCF3mZPR0BpVOE8JyaGjmYpbRKYzRlpraHNOdW6vQFMVj9CnA4MTdm_TUq0egdY5rIwnZSJQrUNQahqxLuSDnkftf89xsGy8s3x8j8TGo.aiqGWA.89TRTKnWGQI5X6MsznTXwScNox0; worklog=.eJw9T8lqAzEM_ZWicw7yIsmeX-mE4EVuBlIK4_gU8u_xJNDL08JbpAdc2i31q3ZYvh_wdZ8FfrX39KNwgnUwprCOEIOZvSitQwTzRA5-HTHI3ERheyDiP_OtEpbJpEaHqrRDpbWtwyFaOD_Ppxm-a7_Cct-HzmmrsICmWNXWYpmlsCE0GLk1MkULoXC0DWvWJFVUQ85ao62ZTA5OxRejpZD3Dr0YLjXFxkhYLMXiOapMP4viWpoxrKjespBDW52r2ZCE-fZldN0_19y2vKU_A88XQENXmA.aiqGWA.WwaMSzNNXqTcpyUUzNRZ2JwMp2M'
    result = get_worklog_tasks(
        uid='1781227526197',
        start_date='2026-06-08',
        end_date='2026-06-15',
        token=token

    )

    if result:
        print("获取成功，返回数据如下：")
        data_list = result['data']
        for log in data_list:
            print('description:', log['description'])
            print('start_date:', log['start_date'])
            print('end_date:', log['end_date'])
            print('---' * 30)
