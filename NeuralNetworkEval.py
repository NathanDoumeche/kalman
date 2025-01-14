import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets
from torchvision.transforms import ToTensor, Lambda, Compose
import matplotlib.pyplot as plt
from utils.nn_dataset import KalmanDataset, KalmanDatasetTronque, compute_normalizing_constants_dataset
import os
from os.path import join
from utils.kalman_networks import NeuralNetwork, NeuralNetwork
from utils.kalman_filter_utils import KalmanFilter1D
import matplotlib.pyplot as plt

# VISUALISATION / COMPARISON OF REALTIME AND NOT REALTIME NETWORK

# path_training_data = "/home/nathan/Bureau/Mines/MAREVA/Mini projet/kalman_dataset/train"
path_training_data = "/home/maud/Documents/mines/mareva/mini_projet/kalman_dataset/train"
mean, std = compute_normalizing_constants_dataset(path_training_data)

path_test_data = "/home/maud/Documents/mines/mareva/mini_projet/kalman_dataset/test_sample"
# path_test_data = "/home/nathan/Bureau/Mines/MAREVA/Mini projet/kalman_dataset/test"
test_dataset = KalmanDataset(path_test_data, mean, std)


batch_size = 1

# Create data loaders.
test_dataloader = DataLoader(test_dataset, batch_size=batch_size)

# MODEL FUTURE
model = NeuralNetwork()
model.load_state_dict(torch.load("checkpoints/model_deep.pth"))
model.eval()

# MODEL REALTIME
model_realtime = NeuralNetwork()
# model_realtime = NeuralNetwork(kernel_size=5, padding=2, padding_mode='reflect')
model_realtime.load_state_dict(torch.load("checkpoints/model_deep_realtime.pth"))
model_realtime.eval()

for  _, (a_vehicle, v_wheel, v_vehicle, idx) in enumerate(test_dataloader):
    with torch.no_grad():

        # pred omniscient
        r_futur = model(a_vehicle, v_wheel)

        a_vehicle_2 = a_vehicle * std[0, 0] + mean[0, 0]
        v_wheel_2 = v_wheel * std[1,0] + mean[1,0]

        pred = KalmanFilter1D(a_vehicle_2, v_wheel_2, r_futur, Q_tab=1, ret_P_hat=False, v_init=v_wheel_2[:,0])

        # pred realtime
        r_hat = []
        L = a_vehicle.shape[1]
        tronc_value = 30

        for t in range(L):
            if t + 1 >= tronc_value:
                a_vehicle_trunc = a_vehicle[:, t + 1 - tronc_value:t + 1]
                v_wheel_trunc = v_wheel[:, t + 1 - tronc_value:t + 1]
            else:
                nb_zeros = tronc_value - t - 1
                zeros_add = torch.zeros((len(a_vehicle), nb_zeros))
                a_vehicle_trunc = torch.cat((zeros_add, a_vehicle[:, 0:t + 1]), dim=1).to(torch.float32)
                v_wheel_trunc = torch.cat((zeros_add, v_wheel[:, 0:t + 1]), dim=1).to(torch.float32)

            # Compute prediction error
            r = model(a_vehicle_trunc, v_wheel_trunc)
            r_hat.append(r[:, 0, -1])

        r_hat = torch.reshape(torch.stack(r_hat), (batch_size, 1, -1))

        a_vehicle = a_vehicle * std[0, 0] + mean[0, 0]
        v_wheel = v_wheel * std[1, 0] + mean[1, 0]
        pred_realtime, _ = KalmanFilter1D(a_vehicle, v_wheel, r_hat, Q_tab=1, ret_P_hat=True, v_init=v_wheel[:, 0])


        fig = plt.figure()
        plt.plot((v_vehicle*std[2,0] + mean[2,0])[0], label='v_vehicle (gt)')
        plt.plot(np.array(v_wheel[0]), '--', label='v_wheel', color="green")
        plt.plot(pred[0], label='v_vehicle estimée (futur)')
        ax = plt.gca()
        ax.set(xlabel="t [s]", ylabel="v [m/s]")
        plt.legend()
        # plt.show()

        fig = plt.figure()
        plt.plot((v_vehicle * std[2, 0] + mean[2, 0])[0],  label='v_vehicle (gt)')
        plt.plot(np.array(v_wheel[0]), '--', label='v_wheel', color="green")
        plt.plot(pred_realtime[0], label='v_vehicle estimée (temps réel)')
        plt.legend()
        ax = plt.gca()
        ax.set(xlabel="t [s]", ylabel="v [m/s]")

        fig = plt.figure()
        plt.plot(r_futur[0, 0], label='R_hat estimé (futur)')
        plt.plot(r_hat[0, 0].detach().numpy(), label='R_hat estimé (temps réel)')
        plt.legend()
        plt.show()


    break
