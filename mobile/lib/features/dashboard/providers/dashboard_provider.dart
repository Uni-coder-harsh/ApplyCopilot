import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';

final dashboardStatsProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final api = ref.watch(apiClientProvider);
  return api.getStats();
});

final dueFollowupsProvider = FutureProvider<List<dynamic>>((ref) async {
  final api = ref.watch(apiClientProvider);
  return api.getDueFollowups();
});
