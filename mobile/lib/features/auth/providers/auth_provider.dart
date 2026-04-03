import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/api_client.dart';

class AuthState {
  final String? token;
  final String? username;
  final bool isLoading;
  final String? error;

  const AuthState({
    this.token,
    this.username,
    this.isLoading = false,
    this.error,
  });

  AuthState copyWith({
    String? token,
    String? username,
    bool? isLoading,
    String? error,
  }) {
    return AuthState(
      token: token ?? this.token,
      username: username ?? this.username,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final ApiClient _api;

  AuthNotifier(this._api) : super(const AuthState()) {
    _loadSavedToken();
  }

  Future<void> _loadSavedToken() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    final username = prefs.getString('username');
    if (token != null) {
      state = state.copyWith(token: token, username: username);
    }
  }

  Future<bool> login(String username, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final data = await _api.login(username, password);
      final token = data['access_token'] as String;
      await _api.saveToken(token);

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('username', username);

      state = state.copyWith(
        token: token,
        username: username,
        isLoading: false,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Invalid username or password',
      );
      return false;
    }
  }

  Future<void> logout() async {
    await _api.clearToken();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('username');
    state = const AuthState();
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final api = ref.watch(apiClientProvider);
  return AuthNotifier(api);
});
