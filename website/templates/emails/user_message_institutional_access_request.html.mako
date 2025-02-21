<%inherit file="notify_base.mako" />

<%def name="content()">
    <tr>
      <td style="border-collapse: collapse;">
        <%!from website import settings%>
        Hello ${recipient.fullname},
        <p>
            This message is coming from an Institutional administrator within your Institution.
        </p>
        % if message_text:
        <p>
            ${message_text}
        </p>
        % endif
        <p>
            Want more information? Visit <a href="${settings.DOMAIN}">${settings.DOMAIN}</a> to learn about OSF, or
            <a href="https://cos.io/">https://cos.io/</a> for information about its supporting organization, the Center
            for Open Science.
        </p>
        <p>
            Questions? Email <a href="mailto:${settings.OSF_CONTACT_EMAIL}">${settings.OSF_CONTACT_EMAIL}</a>
        </p>
      </td>
    </tr>
</%def>
