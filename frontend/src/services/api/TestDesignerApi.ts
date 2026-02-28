import { TestCase, TestRequirement } from '../../types';
import { User } from '../../constants/config';
import { ApiClient } from './ApiClient';

export class TestDesignerApi {
  constructor(private readonly client: ApiClient) {}

  listRequirements(): Promise<TestRequirement[]> {
    return this.client.get<TestRequirement[]>('/requirements');
  }

  createRequirement(payload: TestRequirement): Promise<TestRequirement> {
    return this.client.post<TestRequirement>('/requirements', payload);
  }

  updateRequirement(reqId: string, payload: TestRequirement): Promise<TestRequirement> {
    return this.client.put<TestRequirement>(`/requirements/${reqId}`, payload);
  }

  listTestCases(): Promise<TestCase[]> {
    return this.client.get<TestCase[]>('/test-cases');
  }

  createTestCase(payload: TestCase): Promise<TestCase> {
    return this.client.post<TestCase>('/test-cases', payload);
  }

  updateTestCase(caseId: string, payload: TestCase): Promise<TestCase> {
    return this.client.put<TestCase>(`/test-cases/${caseId}`, payload);
  }

  listUsers(): Promise<User[]> {
    return this.client.get<User[]>('/users');
  }

  createUser(payload: User): Promise<User> {
    return this.client.post<User>('/users', payload);
  }

  updateUser(userId: string, payload: User): Promise<User> {
    return this.client.put<User>(`/users/${userId}`, payload);
  }
}
