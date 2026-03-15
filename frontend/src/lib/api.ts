/**
 * API helpers for NovellaForge.
 *
 * Auth types are re-exported from the central api-client so that they
 * are defined in a single place.  The login / register helpers delegate
 * to authService which already uses the shared `api` client.
 */

export type { AuthResponse, LoginCredentials, RegisterData } from '@/services/api-client'

import { authService } from '@/services/auth.service'
import type { LoginCredentials, RegisterData, AuthResponse } from '@/services/api-client'

export async function login(credentials: LoginCredentials): Promise<AuthResponse> {
  return authService.login(credentials)
}

export async function register(data: RegisterData): Promise<AuthResponse> {
  return authService.register(data)
}

export function setAuthToken(token: string) {
  if (typeof window !== 'undefined') {
    if (!token || token === 'undefined' || token === 'null') {
      localStorage.removeItem('auth_token')
      return
    }
    localStorage.setItem('auth_token', token)
  }
}

export function getAuthToken(): string | null {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('auth_token')
    if (!token || token === 'undefined' || token === 'null') {
      localStorage.removeItem('auth_token')
      return null
    }
    return token
  }
  return null
}

export function removeAuthToken() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('auth_token')
  }
}
