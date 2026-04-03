import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';

final profileProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final api = ref.watch(apiClientProvider);
  return api.getProfile();
});
