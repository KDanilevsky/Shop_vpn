import os
from py3xui import Api, AsyncApi, Inbound, Client
import uuid
import qrcode
import time
from datetime import datetime, timedelta, timezone
from config import QRCODES_DIR

# это для двухфакторной аутентификации, если нужно будет сделать
import pyotp


# Добавление нового клиента
async def add_client_to_3xui_server(async_api, new_client_email,new_expiry_time,new_tg_id):
    flow = "xtls-rprx-vision"
    new_client = await Client(id=str(uuid.uuid4()), email=new_client_email,expiry_time=new_expiry_time,tg_id=new_tg_id,flow=flow, enable=True)
    inbound_id = 1

    await async_api.client.add(inbound_id, [new_client])


# Обновление времени подписки клиента
async def update_existing_3xui_client(async_api, inbounds, user_email, dayz):
    client = await async_api.client.get_by_email(user_email)

    # находим new_expiry_time
    time_now = int(str(time.time()*1000)[:13])
    if time_now > client.expiry_time:
        datetime_now = datetime.now(timezone.utc)
        time_delta = timedelta(days=dayz)
        new_expiry_time = datetime_now + time_delta
        new_expiry_time = int(str(new_expiry_time.timestamp()*1000)[:13])
    else:
        new_expiry_time = int(((client.expiry_time/1000) + (dayz*24*60*60))*1000)

    client.expiry_time = new_expiry_time
    flow = "xtls-rprx-vision"

    client_id = None
    for user_client in inbounds[0].settings.clients:
        if user_client.email == user_email:
            client_id = user_client.id
    # print(client_id)
    # print(type(client_id))
    if client_id is not None:
        client.id = client_id
        await async_api.client.update(client.id, client, flow=flow)

    return new_expiry_time

# удаление всех неактивных клиентов
async def delete_depleted_clients(async_api, inbound):
    inbound_id = 1
    await async_api.client.delete_depleted(inbound_id) # inbound.id


async def delete_client(async_api, tg_id, suff):
    user_email = str(tg_id)+f'-{suff}'
    client = async_api.client.get_by_email(user_email)
    inbound_id = 1

    inbounds: list[Inbound] = async_api.inbound.get_list()
    client_id = None
    for user_client in inbounds[0].settings.clients:
        if user_client.email == user_email:
            client_id = user_client.id

    if client_id is not None:
        client.id = client_id

    async_api.client.delete(inbound_id, client.id)

# Получение ссылки ключа и Создание Qr кода с настройками
async def get_client_settings_string_and_qr(inbounds, user_email, vpn_ip):

    client_setttings_string = None
    usr_list_id = 0
    for user_client in inbounds[0].settings.clients:
        if user_client.email == user_email:
            pbk = inbounds[0].stream_settings.reality_settings['settings']['publicKey']
            fp = inbounds[0].stream_settings.reality_settings['settings']['fingerprint']
            sni = inbounds[0].stream_settings.reality_settings['serverNames'][0]
            sid = inbounds[0].stream_settings.reality_settings['shortIds'][0]
            # client_setttings_string = f'{inbounds[0].protocol}://{inbounds[0].settings.clients[0].id}@{vpn_ip}:{inbounds[0].port}?type={inbounds[0].stream_settings.network}&security={inbounds[0].stream_settings.security}&pbk={pbk}&fp={fp}&sni={sni}&sid={sid}&spx=%2F&flow={inbounds[0].settings.clients[0].flow}#{inbounds[0].settings.clients[0].email}'
            client_setttings_string = f'{inbounds[0].protocol}://{inbounds[0].settings.clients[usr_list_id].id}@{vpn_ip}:{inbounds[0].port}?type={inbounds[0].stream_settings.network}&security={inbounds[0].stream_settings.security}&pbk={pbk}&fp={fp}&sni={sni}&sid={sid}&spx=%2F&flow={inbounds[0].settings.clients[usr_list_id].flow}#{inbounds[0].settings.clients[usr_list_id].email}'
        usr_list_id += 1

    img = qrcode.make(client_setttings_string)
    type(img)  # qrcode.image.pil.PilImage
    img_name = f"{user_email}.png"
    img_path = os.path.join(QRCODES_DIR, img_name)
    img.save(img_path) 

    return client_setttings_string, img_path


# async def choose_server(server_country_id, server_add_rule):
#     # Esli server_add_rule == 1 - to vibirautsa servera tolko s visokim ratingom, esli server_add_rule == 0, to vse krome serverov s visokim raitingom

#     # выбор сервера - дописать алго
#     servers = session.query(AllServers).all()

#     min_servers_count_for_choose_rules = 5
#     procent_servers_bez_dobavlenia = 20
#     chosen_server = None

#     servers_ratings_id_stack = []
    
#     for server in servers:
#         if server.country_id == server_country_id:
#             di = {
#                 "id":server.id,
#                 "country_id":server.country_id,
#                 "rating":server.server_rating,
#                 "subs_count":server.all_subscriptions,
#                 "subs_max":server.max_subscriptions
#                 }
#             servers_ratings_id_stack.append(di)
#     # new_servers_ratings_id_stack = sorted(servers_ratings_id_stack, key=itemgetter('rating'), reverse=True)
#     new_servers_ratings_id_stack = sorted(servers_ratings_id_stack, key=itemgetter('rating'))

#     high_rate_serv_chosen = False
#     for i in range(len(new_servers_ratings_id_stack)):
#         if len(new_servers_ratings_id_stack) >= min_servers_count_for_choose_rules:
#             count_servers_bez_dobavlenya = int((len(new_servers_ratings_id_stack) * procent_servers_bez_dobavlenia) / 100)
#             if server_add_rule == 0:
#                 if i < len(new_servers_ratings_id_stack) - count_servers_bez_dobavlenya: # Esli nado vibrat serv kuda dobavlyaem tolko perenosom izza visokogo ratinga to stavim znak >=
#                     if new_servers_ratings_id_stack[i]["subs_count"] < new_servers_ratings_id_stack[i]["subs_max"]:
#                         chosen_server = int(new_servers_ratings_id_stack[i]["id"])
#             else:
#                 if i >= len(new_servers_ratings_id_stack) - count_servers_bez_dobavlenya:
#                     if new_servers_ratings_id_stack[i]["subs_count"] < new_servers_ratings_id_stack[i]["subs_max"]:
#                         chosen_server = int(new_servers_ratings_id_stack[i]["id"])
#                         high_rate_serv_chosen = True
#         else:
#             if new_servers_ratings_id_stack[i]["subs_count"] < new_servers_ratings_id_stack[i]["subs_max"]:
#                 chosen_server = int(new_servers_ratings_id_stack[i]["id"])

#     # ETO esli mi hotim dobavlyat po ratingu na drugie servera - kogda na servah s visokim ratingom net mesta
#     # esli ne nado - prosto zakomentiruy - togda chosen_server = None
#     if server_add_rule == 1:
#         if len(new_servers_ratings_id_stack) >= min_servers_count_for_choose_rules:
#             if high_rate_serv_chosen is False:
#                 new_servers_ratings_id_stack = sorted(servers_ratings_id_stack, key=itemgetter('rating'), reverse=True)
#                 for i in range(len(new_servers_ratings_id_stack)):
#                     if new_servers_ratings_id_stack[i]["subs_count"] < new_servers_ratings_id_stack[i]["subs_max"]:
#                         chosen_server = int(new_servers_ratings_id_stack[i]["id"])

#     return chosen_server