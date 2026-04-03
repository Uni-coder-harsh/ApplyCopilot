import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

  const ApplyCopilotApp({super.key});
  import 'core/router.dart';
  import 'core/theme.dart';

  void main() {
    runApp(const ProviderScope(child: ApplyCopilotApp()));
  }

  class ApplyCopilotApp extends ConsumerWidget {

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: 'ApplyCopilot',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: ThemeMode.system,
      routerConfig: router,
    );
  }
}
