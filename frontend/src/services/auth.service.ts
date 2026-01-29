import { api } from './api-client'
import type { AuthResponse, LoginCredentials, RegisterData } from './api-client'

export const authService = {
  login: (credentials: LoginCredentials) =>
    api.post<AuthResponse>('/auth/login/json', credentials),
  register: (data: RegisterData) =>
    api.post<AuthResponse>('/auth/register', data),
}
