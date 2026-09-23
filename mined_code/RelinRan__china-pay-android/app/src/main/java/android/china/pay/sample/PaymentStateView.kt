package android.china.pay.sample

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import android.china.pay.core.PayState
import android.china.pay.core.ProviderPayResult
import android.china.pay.wechat.WechatPay

@Composable
fun PaymentStateView(payment: WechatPay) {
    val state by payment.state.collectAsStateWithLifecycle()
    when (state) {
        PayState.Idle -> Unit
        PayState.Launching, PayState.Pending -> LoadingContent()
        is PayState.Success -> SuccessContent((state as PayState.Success<ProviderPayResult>).result)
        PayState.Cancelled -> CancelledContent()
        is PayState.Failure -> FailureContent((state as PayState.Failure).error)
    }
}

@Composable private fun LoadingContent() = Unit
@Composable private fun SuccessContent(result: ProviderPayResult) = Unit
@Composable private fun CancelledContent() = Unit
@Composable private fun FailureContent(error: android.china.pay.core.PayFailure) = Unit
