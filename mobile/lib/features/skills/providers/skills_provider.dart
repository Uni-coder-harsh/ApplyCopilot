import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';

final skillsProvider = FutureProvider<List<dynamic>>((ref) async {
  final api = ref.watch(apiClientProvider);
  return api.getSkills();
});
