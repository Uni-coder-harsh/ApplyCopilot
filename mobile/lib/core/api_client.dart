import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _defaultUrl = 'http://localhost:8000';
const _prefKeyUrl = 'server_url';
const _prefKeyToken = 'auth_token';

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

class ApiClient {
  late final Dio _dio;

  ApiClient() {
    _dio = Dio(BaseOptions(
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
    ));
    _setupInterceptors();
  }

  void _setupInterceptors() {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final prefs = await SharedPreferences.getInstance();
          final baseUrl = prefs.getString(_prefKeyUrl) ?? _defaultUrl;
          final token = prefs.getString(_prefKeyToken);

          options.baseUrl = baseUrl;
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onError: (error, handler) {
          handler.next(error);
        },
      ),
    );
  }

  // ── Auth ────────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> login(String username, String password) async {
    final response = await _dio.post('/api/auth/login', data: {
      'username': username,
      'password': password,
    });
    return response.data;
  }

  Future<Map<String, dynamic>> checkSetup() async {
    final response = await _dio.get('/api/auth/me');
    return response.data;
  }

  Future<void> saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefKeyToken, token);
  }

  Future<void> saveServerUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefKeyUrl, url.trimRight().replaceAll(RegExp(r'/$'), ''));
  }

  Future<String> getServerUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_prefKeyUrl) ?? _defaultUrl;
  }

  Future<void> clearToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_prefKeyToken);
  }

  // ── Applications ────────────────────────────────────────────────────────────

  Future<List<dynamic>> getApplications({
    String? status,
    String? stage,
    String? jobType,
    double? minScore,
    String? search,
    int limit = 50,
  }) async {
    final params = <String, dynamic>{'limit': limit};
    if (status != null) params['status'] = status;
    if (stage != null) params['stage'] = stage;
    if (jobType != null) params['job_type'] = jobType;
    if (minScore != null) params['min_score'] = minScore;
    if (search != null) params['search'] = search;

    final response = await _dio.get('/api/applications/', queryParameters: params);
    return response.data;
  }

  Future<Map<String, dynamic>> getApplicationById(int id) async {
    final response = await _dio.get('/api/applications/$id');
    return response.data;
  }

  Future<Map<String, dynamic>> getStats() async {
    final response = await _dio.get('/api/applications/stats');
    return response.data;
  }

  Future<List<dynamic>> getDueFollowups() async {
    final response = await _dio.get('/api/applications/followups');
    return response.data;
  }

  Future<Map<String, dynamic>> updateApplication(
    int id,
    Map<String, dynamic> data,
  ) async {
    final response = await _dio.patch('/api/applications/$id', data: data);
    return response.data;
  }

  // ── Profile ─────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> getProfile() async {
    final response = await _dio.get('/api/profile/');
    return response.data;
  }

  Future<void> updateProfile(Map<String, dynamic> data) async {
    await _dio.patch('/api/profile/', data: data);
  }

  // ── Skills ──────────────────────────────────────────────────────────────────

  Future<List<dynamic>> getSkills() async {
    final response = await _dio.get('/api/skills/');
    return response.data;
  }

  // ── Resume ──────────────────────────────────────────────────────────────────

  Future<List<dynamic>> getResumes() async {
    final response = await _dio.get('/api/resume/');
    return response.data;
  }

  Future<Map<String, dynamic>> generateResume(int jobId) async {
    final response = await _dio.post('/api/resume/generate/$jobId');
    return response.data;
  }

  // ── Health ──────────────────────────────────────────────────────────────────

  Future<bool> checkHealth() async {
    try {
      final response = await _dio.get('/api/health');
      return response.data['status'] == 'ok';
    } catch (_) {
      return false;
    }
  }
}
